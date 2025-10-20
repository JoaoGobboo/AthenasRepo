import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import GraficoResultados from "../components/GraficoResultados.jsx";
import { fetchResults } from "../services/api.js";

const Resultado = () => {
  const { id } = useParams();
  const [results, setResults] = useState(null);
  const [status, setStatus] = useState("");

  useEffect(() => {
    const loadResults = async () => {
      try {
        const data = await fetchResults(id);
        setResults(data);
      } catch (error) {
        setStatus("Erro ao carregar resultados.");
      }
    };
    loadResults();
  }, [id]);

  if (!results) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-6 text-sm text-slate-300">
        {status || "Carregando resultados..."}
      </div>
    );
  }

  return (
    <section className="space-y-6">
      <header className="rounded-2xl border border-slate-800 bg-slate-950/40 p-6">
        <h2 className="text-2xl font-semibold text-white">{results.election.title}</h2>
        <p className="mt-2 text-sm text-slate-300">{results.election.description}</p>
        <p className="mt-4 text-xs uppercase tracking-wide text-slate-400">
          Fonte dos dados: {results.source === "blockchain" ? "Blockchain Ethereum" : "Base de dados"}
        </p>
      </header>

      <GraficoResultados data={results.results} />

      <div className="rounded-2xl border border-slate-800 bg-slate-950/40 p-6">
        <h3 className="text-lg font-semibold text-white">Resumo</h3>
        <ul className="mt-4 space-y-2 text-sm text-slate-300">
          {results.results.map((result) => (
            <li key={result.candidate} className="flex items-center justify-between">
              <span>{result.candidate}</span>
              <span className="font-semibold">{result.votes} voto(s)</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
};

export default Resultado;
