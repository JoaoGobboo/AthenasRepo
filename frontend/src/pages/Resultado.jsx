import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import GraficoResultados from "../components/GraficoResultados.jsx";
import { fetchResults } from "../services/api.js";

const Resultado = () => {
  const { id } = useParams();
  const [results, setResults] = useState(null);
  const [status, setStatus] = useState("");
  const [isBlockchainLoading, setIsBlockchainLoading] = useState(false);

  useEffect(() => {
    let active = true;
    const loadResults = async () => {
      setStatus("");
      setIsBlockchainLoading(true);
      try {
        const dbData = await fetchResults(id, { includeBlockchain: false });
        if (!active) {
          return;
        }
        setResults(dbData);
        if (dbData.source === "blockchain") {
          setIsBlockchainLoading(false);
          return;
        }
        const chainData = await fetchResults(id);
        if (!active) {
          return;
        }
        if (chainData.source === "blockchain") {
          setResults(chainData);
        }
      } catch (error) {
        if (!active) {
          return;
        }
        setStatus("Erro ao carregar resultados.");
      } finally {
        if (active) {
          setIsBlockchainLoading(false);
        }
      }
    };
    loadResults();
    return () => {
      active = false;
    };
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
          {results.source !== "blockchain" && isBlockchainLoading && " (sincronizando blockchain...)"}
        </p>
      </header>

      <GraficoResultados data={results.results} />

      {isBlockchainLoading && (
        <div className="rounded-xl border border-dashed border-slate-700 bg-slate-950/30 p-4 text-sm text-slate-400">
          Atualizando dados da blockchain...
        </div>
      )}

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
