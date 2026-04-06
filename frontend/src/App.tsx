import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import AppLayout from '@/components/Layout/index';
import Dashboard from '@/pages/Dashboard/index';
import TaskList from '@/pages/TaskList/index';
import TaskDetail from '@/pages/TaskDetail/index';
import MonitorHost from '@/pages/MonitorHost/index';
import MonitorDisk from '@/pages/MonitorDisk/index';
import DeviceManage from '@/pages/DeviceManage/index';
import DataManage from '@/pages/DataManage/index';

const App: React.FC = () => {
  return (
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/tasks" element={<TaskList />} />
            <Route path="/tasks/:id" element={<TaskDetail />} />
            <Route path="/monitor/hosts" element={<MonitorHost />} />
            <Route path="/monitor/disks" element={<MonitorDisk />} />
            <Route path="/devices" element={<DeviceManage />} />
            <Route path="/data" element={<DataManage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
};

export default App;
