import axios from "axios";
export const api = axios.create({ baseURL: "/api", timeout: 20000 });
export const get = (path, params) =>
  api.get(path, { params }).then((r) => r.data);
export function errorText(error) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail
      .map((x) => `${x.loc?.slice(1).join(" · ") || "输入"}：${x.msg}`)
      .join("；");
  return error?.code === "ECONNABORTED"
    ? "请求超时，请稍后重试。"
    : "暂时无法连接服务，请检查后端是否启动后重试。";
}
