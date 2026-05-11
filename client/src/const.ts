export { COOKIE_NAME, ONE_YEAR_MS } from "@shared/const";

// Простая аутентификация - просто возвращаем путь к странице логина
export const getLoginUrl = () => {
  return "/login";
};
