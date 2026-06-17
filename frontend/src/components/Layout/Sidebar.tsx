import React from 'react';
import { Layout, Menu } from 'antd';
import {
  DashboardOutlined,
  UnorderedListOutlined,
  MonitorOutlined,
  DesktopOutlined,
  DatabaseOutlined,
  HddOutlined,
  SwapOutlined,
  ClusterOutlined,
  ExperimentOutlined,
  UpgradeOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { useUiStore } from '@/stores/uiStore';

const { Sider } = Layout;

const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: '仪表盘' },
  { key: '/tasks', icon: <UnorderedListOutlined />, label: '任务管理' },
  {
    key: 'monitor',
    icon: <MonitorOutlined />,
    label: '设备监控',
    children: [
      { key: '/monitor/hosts', icon: <DesktopOutlined />, label: '主机监控' },
      { key: '/monitor/disks', icon: <HddOutlined />, label: '磁盘监控' },
    ],
  },
  { key: '/devices', icon: <DesktopOutlined />, label: '设备管理' },
  { key: '/baselines', icon: <DatabaseOutlined />, label: '基线管理' },
  { key: '/regressions', icon: <SwapOutlined />, label: '回归测试' },
  { key: '/group-tasks', icon: <ClusterOutlined />, label: '多盘并发' },
  { key: '/snia-tasks', icon: <ExperimentOutlined />, label: 'SNIA 测试' },
  { key: '/fw-tests', icon: <UpgradeOutlined />, label: '固件验证' },
  { key: '/data', icon: <DatabaseOutlined />, label: '数据管理' },
];

const Sidebar: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const collapsed = useUiStore((s) => s.sidebarCollapsed);

  const normalizeKey = (path: string) => {
    if (path.startsWith('/devices/')) return '/devices';
    if (path.startsWith('/baselines/')) return '/baselines';
    if (path.startsWith('/regressions/')) return '/regressions';
    if (path.startsWith('/group-tasks/')) return '/group-tasks';
    if (path.startsWith('/snia-tasks/')) return '/snia-tasks';
    if (path.startsWith('/fw-tests/')) return '/fw-tests';
    return path;
  };

  const selectedKey = normalizeKey(location.pathname);
  const openKeys = location.pathname.startsWith('/monitor') ? ['monitor'] : [];

  return (
    <Sider
      collapsible
      collapsed={collapsed}
      trigger={null}
      width={200}
      style={{ background: '#fff' }}
    >
      <div
        style={{
          height: 48,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontWeight: 700,
          fontSize: collapsed ? 14 : 16,
          color: '#1890ff',
          borderBottom: '1px solid #f0f0f0',
        }}
      >
        {collapsed ? 'SSD' : 'SSD 测试平台'}
      </div>
      <Menu
        mode="inline"
        selectedKeys={[selectedKey]}
        defaultOpenKeys={openKeys}
        items={menuItems}
        onClick={({ key }) => navigate(key)}
        style={{ borderRight: 0 }}
      />
    </Sider>
  );
};

export default Sidebar;
