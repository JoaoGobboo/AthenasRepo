import { Link, NavLink, useNavigate } from "react-router-dom";

const navLinks = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/auditoria", label: "Auditoria" }
];

const Navbar = ({ isAuthenticated, onLogout, wallet }) => {
  const navigate = useNavigate();

  const handleLogout = () => {
    onLogout();
    navigate("/login");
  };

  return (
    <header className="bg-slate-950/60 backdrop-blur border-b border-slate-800">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
        <Link to="/" className="text-xl font-semibold text-primary">
          Athenas Voting
        </Link>

        {isAuthenticated && (
          <nav className="flex items-center gap-6 text-sm font-medium text-slate-300">
            {navLinks.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                className={({ isActive }) =>
                  `transition hover:text-primary ${isActive ? "text-primary" : ""}`
                }
              >
                {link.label}
              </NavLink>
            ))}
            <div className="rounded bg-slate-800 px-3 py-1 text-xs uppercase tracking-wide text-slate-200">
              {wallet ? `${wallet.slice(0, 6)}...${wallet.slice(-4)}` : "Conectado"}
            </div>
            <button
              type="button"
              onClick={handleLogout}
              className="rounded-md bg-primary px-3 py-2 text-xs font-semibold uppercase tracking-wide text-white shadow hover:bg-blue-600"
            >
              Sair
            </button>
          </nav>
        )}
      </div>
    </header>
  );
};

export default Navbar;
