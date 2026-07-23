import { useEffect, useRef, useState } from "react";
import { useReducedMotion } from "./useReducedMotion";

export function useAnimatedNumber(target: number, duration = 850) {
  const reducedMotion = useReducedMotion();
  const valueRef = useRef(reducedMotion ? target : 0);
  const [value, setValue] = useState(valueRef.current);
  const [animating, setAnimating] = useState(false);

  useEffect(() => {
    const safeTarget = Number.isFinite(target) ? target : 0;
    if (
      reducedMotion ||
      document.visibilityState === "hidden" ||
      duration <= 0
    ) {
      valueRef.current = safeTarget;
      setValue(safeTarget);
      setAnimating(false);
      return;
    }

    const from = valueRef.current;
    if (Math.abs(from - safeTarget) < Number.EPSILON) return;

    let frame = 0;
    const startedAt = performance.now();
    setAnimating(true);

    const tick = (now: number) => {
      const progress = Math.min(1, (now - startedAt) / duration);
      const eased = 1 - Math.pow(1 - progress, 3);
      const next = from + (safeTarget - from) * eased;
      valueRef.current = next;
      setValue(next);

      if (progress < 1) {
        frame = window.requestAnimationFrame(tick);
      } else {
        valueRef.current = safeTarget;
        setValue(safeTarget);
        setAnimating(false);
      }
    };

    frame = window.requestAnimationFrame(tick);
    return () => window.cancelAnimationFrame(frame);
  }, [duration, reducedMotion, target]);

  return { value, animating };
}
