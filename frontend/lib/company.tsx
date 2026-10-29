"use client";
import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { api } from "./api";

type CompanyContextType = {
  companyName: string;
  source: string;
  isLoading: boolean;
  setCompanyName: (name: string) => Promise<void>;
  refreshCompany: () => Promise<void>;
};

const CompanyContext = createContext<CompanyContextType>({
  companyName: "Business Gate",
  source: "default",
  isLoading: false,
  setCompanyName: async () => {},
  refreshCompany: async () => {},
});

const STORAGE_KEY = "mb_company_name";

export function CompanyProvider({ children }: { children: ReactNode }) {
  const [companyName, setCompanyNameState] = useState<string>(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem(STORAGE_KEY) || "Business Gate";
    }
    return "Business Gate";
  });
  const [source, setSource] = useState<string>("default");
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchCompany = async () => {
    try {
      const data = await api("/system/company");
      if (data?.company_name) {
        setCompanyNameState(data.company_name);
        setSource(data.source || "data");
        localStorage.setItem(STORAGE_KEY, data.company_name);
      }
    } catch {
      // Keep stored / default on network failure or auth redirect
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCompany();
  }, []);

  const updateCompany = async (name: string) => {
    const data = await api("/system/company", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
    if (data?.company_name) {
      setCompanyNameState(data.company_name);
      setSource(data.source || "user");
      localStorage.setItem(STORAGE_KEY, data.company_name);
    }
  };

  return (
    <CompanyContext.Provider
      value={{
        companyName,
        source,
        isLoading,
        setCompanyName: updateCompany,
        refreshCompany: fetchCompany,
      }}
    >
      {children}
    </CompanyContext.Provider>
  );
}

export const useCompany = () => useContext(CompanyContext);
