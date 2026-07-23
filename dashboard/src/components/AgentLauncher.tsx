import { useEffect, useRef, useState } from "react";
import type { CSSProperties, PointerEvent as ReactPointerEvent } from "react";

type Props = {
  open: boolean;
  onClick: () => void;
};

type Position = {
  left: number;
  top: number;
};

const STORAGE_KEY = "reviewops-launcher-position-v1";
const EDGE_GAP = 8;

function readSavedPosition(): Position | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const value = JSON.parse(raw) as Partial<Position>;
    if (!Number.isFinite(value.left) || !Number.isFinite(value.top)) return null;
    return { left: Number(value.left), top: Number(value.top) };
  } catch {
    return null;
  }
}

export function AgentLauncher({ open, onClick }: Props) {
  const buttonRef = useRef<HTMLButtonElement>(null);
  const dragRef = useRef<{
    pointerId: number;
    startX: number;
    startY: number;
    offsetX: number;
    offsetY: number;
    moved: boolean;
  } | null>(null);
  const suppressClickRef = useRef(false);
  const [position, setPosition] = useState<Position | null>(readSavedPosition);
  const [dragging, setDragging] = useState(false);

  function clampPosition(left: number, top: number): Position {
    const rect = buttonRef.current?.getBoundingClientRect();
    const width = rect?.width || 176;
    const height = rect?.height || 54;
    return {
      left: Math.min(
        Math.max(EDGE_GAP, left),
        Math.max(EDGE_GAP, window.innerWidth - width - EDGE_GAP),
      ),
      top: Math.min(
        Math.max(EDGE_GAP, top),
        Math.max(EDGE_GAP, window.innerHeight - height - EDGE_GAP),
      ),
    };
  }

  useEffect(() => {
    if (!position) return;
    const next = clampPosition(position.left, position.top);
    if (next.left !== position.left || next.top !== position.top) {
      setPosition(next);
      return;
    }
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  }, [position]);

  useEffect(() => {
    const onResize = () => {
      setPosition((current) =>
        current ? clampPosition(current.left, current.top) : current,
      );
    };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  function onPointerDown(event: ReactPointerEvent<HTMLButtonElement>) {
    if (event.button !== 0) return;
    const rect = event.currentTarget.getBoundingClientRect();
    dragRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      offsetX: event.clientX - rect.left,
      offsetY: event.clientY - rect.top,
      moved: false,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function onPointerMove(event: ReactPointerEvent<HTMLButtonElement>) {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    const distance = Math.hypot(
      event.clientX - drag.startX,
      event.clientY - drag.startY,
    );
    if (!drag.moved && distance < 4) return;
    drag.moved = true;
    setDragging(true);
    setPosition(
      clampPosition(
        event.clientX - drag.offsetX,
        event.clientY - drag.offsetY,
      ),
    );
  }

  function finishDrag(event: ReactPointerEvent<HTMLButtonElement>) {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    suppressClickRef.current = drag.moved;
    dragRef.current = null;
    setDragging(false);
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  }

  const style: CSSProperties | undefined = position
    ? {
        left: `${position.left}px`,
        top: `${position.top}px`,
        right: "auto",
        bottom: "auto",
      }
    : undefined;

  return (
    <button
      ref={buttonRef}
      type="button"
      className={`reviewops-launcher ${open ? "is-open" : ""} ${
        dragging ? "is-dragging" : ""
      }`}
      style={style}
      aria-expanded={open}
      aria-controls="reviewops-drawer"
      aria-label="AI 风险调查，可拖动位置"
      title="拖动可调整位置，点击打开 AI 风险调查"
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={finishDrag}
      onPointerCancel={finishDrag}
      onClick={() => {
        if (suppressClickRef.current) {
          suppressClickRef.current = false;
          return;
        }
        onClick();
      }}
    >
      <span className="reviewops-launcher__pulse" aria-hidden />
      <span>
        <small>REVIEWOPS COPILOT</small>
        AI 风险调查
      </span>
      <b aria-hidden>{open ? "×" : "↔"}</b>
    </button>
  );
}
