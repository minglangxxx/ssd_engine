import React from 'react';
import { Spin } from 'antd';

const LoadingOverlay: React.FC<{ loading: boolean; children: React.ReactNode }> = ({
  loading,
  children,
}) => {
  return <Spin spinning={loading}>{children}</Spin>;
};

export default LoadingOverlay;
