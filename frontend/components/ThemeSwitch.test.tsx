import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, beforeEach } from "vitest";
import { ThemeSwitch } from "./ThemeSwitch";
import { useTheme } from "@/lib/theme";

describe("ThemeSwitch", () => {
  beforeEach(() => {
    useTheme.setState({ mode: "light" });
    document.documentElement.setAttribute("data-theme", "light");
  });

  it("renders with proper accessibility labels", () => {
    render(<ThemeSwitch />);
    const button = screen.getByRole("button", { name: /switch to dark mode/i });
    expect(button).toBeDefined();
  });

  it("toggles between light and dark on click", () => {
    render(<ThemeSwitch />);
    const button = screen.getByRole("button", { name: /switch to dark mode/i });
    fireEvent.click(button);
    expect(useTheme.getState().mode).toBe("dark");
  });
});
