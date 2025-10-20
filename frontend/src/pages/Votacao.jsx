import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { fetchElections, submitVote } from "../services/api.js";

const Votacao = ({ wallet }) => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [election, setElection] = useState(null);
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const loadElection = async () => {
      const elections = await fetchElections();
      const found = elections.find((item) => item.id === Number(id));
      setElection(found || null);
    };
    loadElection();
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
      const response = await submitVote({
        electionId: Number(id),
        candidateId: Number(selectedCandidate)
      });
      setStatus(response.blockchain?.message || "Voto registrado!");
      setTimeout(() => navigate(`/resultado/${id}`), 1500);
    } catch (error) {
      setStatus(error.response?.data?.message || "Erro ao registrar voto.");
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
