import { lazy, Suspense } from "react";
import type { LaserVariantsProps, ThreeUILaserVariant } from "./LaserVariants";

export type LaserVariant = "matrix-field" | ThreeUILaserVariant;

export type LaserCollectionProps = LaserVariantsProps & {
  variant?: LaserVariant;
};

const LaserVariantsRenderer = lazy(() =>
  import("./LaserVariants").then((module) => ({ default: module.LaserVariants })),
);

const FALLBACK = <div className="threeui-background laser-variant" style={{ background: '#030705' }} />;

export function LaserCollection({ variant = "atmospheric-blade", ...props }: LaserCollectionProps) {
  const laserVariant: ThreeUILaserVariant =
    (variant as string) === "matrix-field" ? "atmospheric-blade" : (variant as ThreeUILaserVariant);

  return (
    <Suspense fallback={FALLBACK}>
      <LaserVariantsRenderer {...props} variant={laserVariant} />
    </Suspense>
  );
}

export default LaserCollection;
