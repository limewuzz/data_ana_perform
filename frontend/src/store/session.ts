import { create } from "zustand";
import type { Role, User } from "@/lib/api";

type SessionState = {
  token: string | null;
  user: User | null;
  setToken: (token: string | null) => void;
  setUser: (user: User | null) => void;
  logout: () => void;
  role: () => Role | null;
};

const storedToken = localStorage.getItem("pdaw_token");
const storedUser = localStorage.getItem("pdaw_user");

export const useSessionStore = create<SessionState>((set, get) => ({
  token: storedToken,
  user: storedUser ? (JSON.parse(storedUser) as User) : null,
  setToken: (token) => {
    if (token) localStorage.setItem("pdaw_token", token);
    else localStorage.removeItem("pdaw_token");
    set({ token });
  },
  setUser: (user) => {
    if (user) localStorage.setItem("pdaw_user", JSON.stringify(user));
    else localStorage.removeItem("pdaw_user");
    set({ user });
  },
  logout: () => {
    localStorage.removeItem("pdaw_token");
    localStorage.removeItem("pdaw_user");
    set({ token: null, user: null });
  },
  role: () => get().user?.role ?? null,
}));
