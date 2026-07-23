import { useAnimatedNumber } from "../hooks/useAnimatedNumber";

type Props = {
  value: number;
  format: (value: number) => string;
  className?: string;
  duration?: number;
};

export function AnimatedNumber({
  value,
  format,
  className,
  duration,
}: Props) {
  const animated = useAnimatedNumber(value, duration);
  const classes = [
    className,
    animated.animating ? "is-number-animating" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <strong className={classes} aria-label={format(value)}>
      {format(animated.value)}
    </strong>
  );
}
