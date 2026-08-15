import { NavLink } from "react-router-dom";
import { usePresentation } from "../lib/presentation";

export default function Nav() {
  const { demo, toggle } = usePresentation();
  const linkCls = ({ isActive }: { isActive: boolean }) =>
    "nav__link" + (isActive ? " nav__link--active" : "");

  return (
    <header className="nav">
      <div className="nav__inner">
        <div className="nav__brand">
          <span className="nav__mark">宇</span>
          <span className="nav__word">YU</span>
        </div>
        <nav className="nav__links" aria-label="主导航">
          <NavLink to="/" end className={linkCls}>
            Cockpit
          </NavLink>
          <NavLink to="/memory" className={linkCls}>
            Memory
          </NavLink>
        </nav>
        <div className="nav__actions">
          <button
            className={"nav__pill" + (demo ? " nav__pill--on" : "")}
            onClick={toggle}
            title="Presentation Mode：隐藏私人信息，适合录屏"
          >
            <span className="nav__pill-dot" />
            {demo ? "Demo" : "Private"}
          </button>
        </div>
      </div>
    </header>
  );
}
