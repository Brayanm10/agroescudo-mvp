import { AgroTrendChart, type AgroTrendChartProps } from "./AgroTrendChart";

export function AgroTemperatureChart(props: Omit<AgroTrendChartProps, "title" | "eyebrow" | "color" | "variant">) {
  return (
    <AgroTrendChart
      {...props}
      title="Temperatura del grano"
      eyebrow="Condición térmica"
      description="Serie principal para detectar acumulación térmica y verificar la respuesta operativa"
      color="#064f3b"
      variant="primary"
    />
  );
}
