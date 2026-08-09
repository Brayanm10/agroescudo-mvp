import { AgroTrendChart, type AgroTrendChartProps } from "./AgroTrendChart";

export function AgroHumidityChart(props: Omit<AgroTrendChartProps, "title" | "eyebrow" | "color" | "variant">) {
  return (
    <AgroTrendChart
      {...props}
      title="Humedad ambiente"
      eyebrow="Condición ambiental"
      description="Evolución de humedad y eventos registrados durante el periodo"
      color="#d99a00"
      variant="secondary"
      percentage
    />
  );
}
