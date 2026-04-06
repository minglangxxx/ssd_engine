import axios, { AxiosInstance } from 'axios';
import { message } from 'antd';

const request: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 30000,
});

request.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error)
);

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const msg =
      error.response?.data?.error?.message ||
      error.response?.data?.message ||
      '请求失败';
    message.error(msg);
    return Promise.reject(error);
  }
);

export default request;
