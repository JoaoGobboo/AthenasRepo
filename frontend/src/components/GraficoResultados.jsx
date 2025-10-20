import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

const GraficoResultados = ({ data }) => {
  const chartData = data.map((item) => ({
    name: item.candidate,
    votos: item.votes
  }));

  return (
    <div className="h-80 w-full rounded-xl border border-slate-800 bg-slate-950/40 p-4">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData}>
          <XAxis dataKey="name" stroke="#94a3b8" />
          <YAxis allowDecimals={false} stroke="#94a3b8" />
          <Tooltip
            cursor={{ fill: "rgba(37, 99, 235, 0.2)" }}
            contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #1e293b" }}
          />
          <Bar dataKey="votos" fill="#2563eb" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default GraficoResultados;
