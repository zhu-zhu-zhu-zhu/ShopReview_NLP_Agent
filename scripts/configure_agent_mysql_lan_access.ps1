[CmdletBinding()]
param(
  [string]$AgentIp='',
  [int]$Port=3306,
  [switch]$ValidateOnly,
  [switch]$RemoveOldRule
)

$ErrorActionPreference='Stop'
$ContainerName='shopreview_mysql'
$RulePrefix='ShopReview MySQL Agent '

function Assert-Exit([string]$Stage){
  if($LASTEXITCODE -ne 0){throw "$Stage failed with exit code $LASTEXITCODE"}
}

function Test-PrivateIPv4([string]$Value){
  $Parsed=$null
  if(-not [System.Net.IPAddress]::TryParse($Value,[ref]$Parsed)){return $false}
  if($Parsed.AddressFamily -ne [System.Net.Sockets.AddressFamily]::InterNetwork){return $false}
  $Bytes=$Parsed.GetAddressBytes()
  if($Bytes[0] -eq 10){return $true}
  if($Bytes[0] -eq 172 -and $Bytes[1] -ge 16 -and $Bytes[1] -le 31){return $true}
  if($Bytes[0] -eq 192 -and $Bytes[1] -eq 168){return $true}
  return $false
}

function Get-ActivePrivateLan{
  $Candidates=@(
    Get-NetIPConfiguration |
      Where-Object {
        $_.NetAdapter.Status -eq 'Up' -and
        $_.IPv4DefaultGateway -ne $null -and
        $_.InterfaceAlias -notmatch 'Loopback|Docker|vEthernet|Hyper-V|WSL'
      }
  )
  $PrivateCandidates=@()
  foreach($Candidate in $Candidates){
    $Profile=Get-NetConnectionProfile -InterfaceIndex $Candidate.InterfaceIndex -ErrorAction SilentlyContinue
    if($Profile.NetworkCategory -eq 'Private'){
      foreach($Address in $Candidate.IPv4Address){
        if(Test-PrivateIPv4 $Address.IPAddress){
          $PrivateCandidates += [pscustomobject]@{
            Adapter=$Candidate.InterfaceAlias
            Address=$Address.IPAddress
            Gateway=($Candidate.IPv4DefaultGateway.NextHop -join ',')
            Category=$Profile.NetworkCategory
          }
        }
      }
    }
  }
  if($PrivateCandidates.Count -ne 1){throw "Expected one active Private LAN IPv4; found $($PrivateCandidates.Count)"}
  return $PrivateCandidates[0]
}

function Get-RuleDetails([string]$DisplayName){
  $Rules=@(Get-NetFirewallRule -DisplayName $DisplayName -ErrorAction SilentlyContinue)
  if($Rules.Count -gt 1){throw "Duplicate firewall rules found: $DisplayName"}
  if($Rules.Count -eq 0){return $null}
  $Rule=$Rules[0]
  $PortFilter=$Rule|Get-NetFirewallPortFilter
  $AddressFilter=$Rule|Get-NetFirewallAddressFilter
  return [pscustomobject]@{
    Rule=$Rule
    PortFilter=$PortFilter
    AddressFilter=$AddressFilter
  }
}

try{
  Write-Host '[1/5] Agent IP and network-profile safety'
  if($Port -lt 1 -or $Port -gt 65535){throw 'Port must be between 1 and 65535'}
  if($AgentIp -and -not(Test-PrivateIPv4 $AgentIp)){
    throw 'AgentIp must be one explicit RFC1918 IPv4; Any, wildcards, loopback and public addresses are rejected'
  }
  if(-not $ValidateOnly -and -not $AgentIp){
    throw 'AgentIp is required. Ask the Agent developer for the active private IPv4 of their laptop.'
  }
  $Lan=Get-ActivePrivateLan
  Write-Host "ActiveAdapter=$($Lan.Adapter) CurrentLanIPv4=$($Lan.Address) Profile=$($Lan.Category)"

  Write-Host '[2/5] Dedicated MySQL container and port mapping'
  $ContainerState=(& docker inspect $ContainerName --format '{{.State.Running}}').Trim()
  Assert-Exit 'Docker container inspection'
  if($ContainerState -ne 'true'){throw "$ContainerName is not running"}
  $PortLines=@(& docker port $ContainerName 3306/tcp)
  Assert-Exit 'Docker port inspection'
  if(-not($PortLines -match "0\.0\.0\.0:$Port")){throw "Container port 3306 is not mapped to 0.0.0.0:$Port"}

  Write-Host '[3/5] Local and LAN host-port validation'
  if(-not(Test-NetConnection 127.0.0.1 -Port $Port -InformationLevel Quiet)){throw "127.0.0.1:$Port is unavailable"}
  if(-not(Test-NetConnection $Lan.Address -Port $Port -InformationLevel Quiet)){throw "$($Lan.Address):$Port is unavailable locally"}
  Write-Host 'LocalMySqlTcp=PASS LanHostMySqlTcp=PASS'

  Write-Host '[4/5] Narrow Private firewall rule'
  if(-not $AgentIp){
    Write-Host 'AgentIp=MISSING; no firewall modification performed.'
    Write-Host 'Request this from the Agent developer: active private IPv4 from the adapter with a default gateway.'
    Write-Host 'Command for Agent laptop: Get-NetIPConfiguration | Where-Object {$_.IPv4DefaultGateway -ne $null} | Select-Object InterfaceAlias,IPv4Address,IPv4DefaultGateway'
    Write-Host '[5/5] Result: PENDING_AGENT_IP'
    exit 0
  }

  $DisplayName=$RulePrefix+$AgentIp
  if($RemoveOldRule -and -not $ValidateOnly){
    $OldRules=@(Get-NetFirewallRule -ErrorAction SilentlyContinue|Where-Object{$_.DisplayName -like "$RulePrefix*" -and $_.DisplayName -ne $DisplayName})
    foreach($OldRule in $OldRules){
      if(-not $OldRule.DisplayName.StartsWith($RulePrefix)){throw 'Refusing to remove an unrelated firewall rule'}
      Remove-NetFirewallRule -Name $OldRule.Name
    }
  }

  $Details=Get-RuleDetails $DisplayName
  if(-not $Details -and -not $ValidateOnly){
    New-NetFirewallRule -DisplayName $DisplayName -Direction Inbound -Action Allow `
      -Protocol TCP -LocalPort $Port -Profile Private -RemoteAddress $AgentIp|Out-Null
    $Details=Get-RuleDetails $DisplayName
  }
  if(-not $Details){
    Write-Host "FirewallRule=$DisplayName Status=MISSING"
    Write-Host '[5/5] Result: PENDING_RULE_CREATION'
    exit 2
  }
  $Rule=$Details.Rule
  $PortFilter=$Details.PortFilter
  $AddressFilter=$Details.AddressFilter
  if($Rule.Enabled -ne 'True' -or $Rule.Direction -ne 'Inbound' -or $Rule.Action -ne 'Allow'){
    throw 'Firewall rule action/direction/enabled state is unsafe'
  }
  if($Rule.Profile -notmatch 'Private' -or $Rule.Profile -match 'Public|Any'){
    throw 'Firewall rule must use only the Private profile'
  }
  if($PortFilter.Protocol -ne 'TCP' -or $PortFilter.LocalPort -notcontains [string]$Port){
    throw 'Firewall rule protocol or port mismatch'
  }
  if($AddressFilter.RemoteAddress.Count -ne 1 -or $AddressFilter.RemoteAddress[0] -ne $AgentIp){
    throw 'Firewall rule RemoteAddress is not the exact AgentIp'
  }
  Write-Host "FirewallRule=$DisplayName Profile=Private RemoteAddress=$AgentIp Port=$Port Status=PASS"
  Write-Host '[5/5] Result: PASS'
  exit 0
}catch{
  Write-Error $_
  exit 1
}
