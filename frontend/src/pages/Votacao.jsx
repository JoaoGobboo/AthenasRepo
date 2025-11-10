import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { fetchElections, submitVote } from "../services/api.js";
import { voteOnChain } from "../services/blockchain.js";
import { loadCache, saveCache } from "../utils/cache.js";

const Votacao = ({ wallet }) => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [election, setElection] = useState(null);
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);
  const CACHE_KEY = "dashboard-elections";
  const CACHE_TTL_SECONDS = 30;

  useEffect(() => {
    let active = true;
    const hydrateFromCache = () => {
      const cached = loadCache(CACHE_KEY, CACHE_TTL_SECONDS);
      if (cached) {
        const found = cached.find((item) => item.id === Number(id));
        if (found) {
          setElection(found);
        }
      }
    };

    const loadElection = async () => {
      try {
        const elections = await fetchElections();
        if (!active) {
          return;
        }
        saveCache(CACHE_KEY, elections);
        const found = elections.find((item) => item.id === Number(id));
        setElection(found || null);
      } catch (error) {
        if (active) {
          setElection(null);
          setStatus("Erro ao carregar eleição.");
        }
      }
    };

    hydrateFromCache();
    loadElection();

    return () => {
      active = false;
    };
  }, [id]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!selectedCandidate) {
      setStatus("Selecione um candidato antes de votar.");
      return;
    }
    setLoading(true);
    setStatus("");
    try {
      const chainElectionId = Math.max(0, Number(id) - 1);
      const candidateIndex = election.candidates.findIndex(
        (candidate) => candidate.id === Number(selectedCandidate)
      );
      if (candidateIndex === -1) {
        setStatus("Candidato não encontrado.");
        return;
      }
      const txHash = await voteOnChain(chainElectionId, candidateIndex);
      const response = await submitVote({
        electionId: Number(id),
        candidateId: Number(selectedCandidate),
        txHash
      });
      setStatus(response.blockchain?.message || "Voto registrado!");
      setTimeout(() => navigate(`/resultado/${id}`), 1500);
    } catch (error) {
      if (error?.code === 4001) {
        setStatus("Transação cancelada pelo usuário.");
      } else {
        setStatus(error.response?.data?.message || error.message || "Erro ao registrar voto.");
      }
    } finally {
      setLoading(false);
    }
  };

  if (!election) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-6 text-sm text-slate-300">
        Carregando eleição...
      </div>
    );
  }

  return (
    <section className="mx-auto max-w-2xl space-y-6">
      <header>
        <h2 className="text-2xl font-semibold text-white">{election.title}</h2>
        <p className="mt-2 text-sm text-slate-300">{election.description}</p>
        <p className="mt-2 text-xs uppercase tracking-wide text-slate-400">
          Carteira ativa: {wallet ? `${wallet.slice(0, 6)}...${wallet.slice(-4)}` : "Não conectada"}
        </p>
      </header>

      <form onSubmit={handleSubmit} className="space-y-4 rounded-2xl border border-slate-800 bg-slate-950/40 p-6">
        <h3 className="text-lg font-semibold text-white">Escolha seu candidato</h3>
        <div className="space-y-3">
          {election.candidates.map((candidate) => (
            <label
              key={candidate.id}
              className={`flex cursor-pointer items-center justify-between rounded-lg border px-4 py-3 ${
                Number(selectedCandidate) === candidate.id
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-slate-800 text-slate-200 hover:border-primary/50"
              }`}
            >
              <span className="text-sm font-medium">{candidate.name}</span>
              <input
                type="radio"
                name="candidate"
                value={candidate.id}
                checked={Number(selectedCandidate) === candidate.id}
                onChange={(event) => setSelectedCandidate(event.target.value)}
              />
            </label>
          ))}
        </div>
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-blue-600 disabled:bg-blue-400"
        >
          {loading ? "Enviando voto..." : "Confirmar voto"}
        </button>
        {status && <p className="text-sm text-slate-300">{status}</p>}
      </form>
    </section>
  );
};

export default Votacao;
