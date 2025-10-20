const CardEleicao = ({ election, onVote, onResults }) => {
  const { id, title, description, candidates } = election;

  return (
    <article className="rounded-xl border border-slate-800 bg-slate-950/40 p-6 shadow">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-lg font-semibold text-white">{title}</h3>
          <p className="mt-2 text-sm text-slate-300">{description}</p>
        </div>
        <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
          {candidates.length} candidatos
        </span>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {candidates.map((candidate) => (
          <span
            key={candidate.id ?? candidate.name}
            className="rounded-full bg-slate-800 px-3 py-1 text-xs font-medium text-slate-200"
          >
            {candidate.name}
          </span>
        ))}
      </div>

      <div className="mt-6 flex gap-3">
        <button
          type="button"
          onClick={() => onVote(id)}
          className="flex-1 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-blue-600"
        >
          Votar
        </button>
        <button
          type="button"
          onClick={() => onResults(id)}
          className="flex-1 rounded-lg border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-200 hover:border-primary hover:text-primary"
        >
          Resultados
        </button>
      </div>
    </article>
  );
};

export default CardEleicao;
