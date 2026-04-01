import { useCallback, useState } from "react";
import {
  dashboardApi,
  type BotCommentsResponse,
  type GlobalDashboardResponse,
  type UserDashboardResponse,
  type VideoDashboardResponse,
} from "../api/dashboard";
import { dataApi, type DataCollection } from "../api/data";
import { useAuthContext } from "../contexts/AuthContext";

export function useDashboard() {
  const { token } = useAuthContext();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Dados
  const [globalData, setGlobalData] = useState<GlobalDashboardResponse | null>(null);
  const [videoData, setVideoData] = useState<VideoDashboardResponse | null>(null);
  const [userData, setUserData] = useState<UserDashboardResponse | null>(null);
  const [botsData, setBotsData] = useState<BotCommentsResponse | null>(null);
  const [collections, setCollections] = useState<DataCollection[]>([]);

  // Filtro de critérios ativo
  const [activeCriteria, setActiveCriteria] = useState<string[]>([]);

  const fetchGlobal = useCallback(
    async (criteria?: string[]) => {
      if (!token) return;
      setLoading(true);
      setError(null);
      try {
        const data = await dashboardApi.global(token, criteria);
        setGlobalData(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erro ao carregar dashboard.");
      } finally {
        setLoading(false);
      }
    },
    [token]
  );

  const fetchVideo = useCallback(
    async (videoId: string, criteria?: string[]) => {
      if (!token) return;
      setLoading(true);
      setError(null);
      try {
        const data = await dashboardApi.video(token, videoId, criteria);
        setVideoData(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erro ao carregar dados do vídeo.");
      } finally {
        setLoading(false);
      }
    },
    [token]
  );

  const fetchUser = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const data = await dashboardApi.user(token);
      setUserData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar progresso.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  const fetchBots = useCallback(
    async (params?: {
      dataset_id?: string;
      author?: string;
      search?: string;
      page?: number;
      page_size?: number;
    }) => {
      if (!token) return;
      try {
        const data = await dashboardApi.bots(token, params);
        setBotsData(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erro ao carregar tabela de bots.");
      }
    },
    [token]
  );

  const fetchCollections = useCallback(async () => {
    if (!token) return;
    try {
      const data = await dataApi.collections(token);
      setCollections(data);
    } catch {
      // silencioso — collections é auxiliar para o dropdown
    }
  }, [token]);

  return {
    loading,
    error,
    globalData,
    videoData,
    userData,
    botsData,
    collections,
    activeCriteria,
    setActiveCriteria,
    fetchGlobal,
    fetchVideo,
    fetchUser,
    fetchBots,
    fetchCollections,
  };
}
