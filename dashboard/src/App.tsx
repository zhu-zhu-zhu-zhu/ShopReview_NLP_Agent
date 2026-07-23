import { getApiBase } from "./api";
import { useServingBoardData } from "./hooks/useServingBoardData";
import { CommandWall } from "./variants/CommandWall";

export default function App() {
  const board = useServingBoardData();

  if (board.error) {
    return (
      <div className="wall-boot">
        <strong>后端不可用</strong>
        <p>{board.error}</p>
        <p className="mono">API {getApiBase()}</p>
        <button type="button" onClick={() => void board.reload(true)}>
          重试
        </button>
      </div>
    );
  }

  if (!board.data) {
    return (
      <div className="wall-boot">
        <p>正在同步服务库指标…</p>
      </div>
    );
  }

  return (
    <CommandWall
      data={board.data}
      onRefresh={() => void board.reload(true)}
      loading={board.loading}
    />
  );
}
