import React from 'react';
import { Layout, Button } from 'antd';
import { MenuFoldOutlined, MenuUnfoldOutlined } from '@ant-design/icons';
import { useUiStore } from '@/stores/uiStore';

const { Header: AntHeader } = Layout;

const Header: React.FC = () => {
  const collapsed = useUiStore((s) => s.sidebarCollapsed);
  const toggleSidebar = useUiStore((s) => s.toggleSidebar);

  return (
    <AntHeader
      style={{
        background: '#fff',
        padding: '0 24px',
        display: 'flex',
        alignItems: 'center',
        borderBottom: '1px solid #f0f0f0',
        height: 48,
      }}
    >
      <Button
        type="text"
        icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
        onClick={toggleSidebar}
      />
      <span style={{ marginLeft: 16, fontSize: 16, fontWeight: 600 }}>
        SSD 性能测试平台
      </span>
    </AntHeader>
  );
};

export default Header;
