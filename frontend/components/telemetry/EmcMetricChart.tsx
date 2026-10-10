"use client";

import type { CanonicalMetricSeries } from "@/lib/types";
import { AgroTrendChart } from "@/components/charts";
import { toEmcChartPoints } from "./emc-model";

export function EmcMetricChart({ series, periodLabel, resolutionLabel }: { series: CanonicalMetricSeries; periodLabel?: string; resolutionLabel?: string }) {
  const points = toEmcChartPoints(series);
  return (
    <div className="xl:col-span-2">
      <AgroTrendChart
        title="Humedad del grano estimada por EMC"
        eyebrow="Estimación dinámica · Modified Chung-Pfost"
        description={`Modelo Chung-Pfost · Maíz · ${series.points.at(-1)?.calibration_offset_pp == null ? "Estimación EMC sin calibración local" : "Estimación EMC con calibración local"}`}
        points={points}
        summary={series.summary}
        gaps={series.gaps}
        thresholds={{}}
        unit="% wb"
        decimals={1}
        color="#8a5a14"
        periodLabel={periodLabel}
        resolutionLabel={resolutionLabel}
        variant="primary"
        percentage
        variationUnit=" pp"
      />
    </div>
  );
}
