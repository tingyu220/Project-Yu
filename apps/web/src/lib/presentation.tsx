// Presentation / Demo 模式：隐藏敏感信息，适合录屏。
// 通过 ?demo=true 进入，也可在导航栏切换。
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

interface PresentationValue {
  demo: boolean;
  toggle: () => void;
  /** demo 模式下把敏感文本替换为掩码。 */
  mask: (text: string) => string;
}

const Ctx = createContext<PresentationValue>({
  demo: false,
  toggle: () => {},
  mask: (t) => t,
});

export function PresentationProvider({ children }: { children: ReactNode }) {
  const [demo, setDemo] = useState<boolean>(() =>
    typeof window !== "undefined" && new URLSearchParams(window.location.search).get("demo") === "true",
  );

  const toggle = useCallback(() => setDemo((v) => !v), []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (demo) params.set("demo", "true");
    else params.delete("demo");
    const qs = params.toString();
    window.history.replaceState(null, "", qs ? "?" + qs : window.location.pathname);
  }, [demo]);

  const value = useMemo<PresentationValue>(
    () => ({
      demo,
      toggle,
      mask: (text) => (demo ? "••••••" : text),
    }),
    [demo, toggle],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function usePresentation(): PresentationValue {
  return useContext(Ctx);
}
