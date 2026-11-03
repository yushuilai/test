import { useState } from 'react';
import { Form, Input, Button, Checkbox, Card, Typography, message } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';

export interface LoginFormValues {
  username: string;
  password: string;
  remember?: boolean;
}

interface LoginPageProps {
  /** 登录提交回调，用于替换默认的 mock 登录行为（便于测试与接入真实接口） */
  onFinish?: (values: LoginFormValues) => void | Promise<void>;
}

export default function LoginPage({ onFinish }: LoginPageProps) {
  const [loading, setLoading] = useState(false);

  const handleFinish = async (values: LoginFormValues) => {
    setLoading(true);
    try {
      if (onFinish) {
        await onFinish(values);
      } else {
        message.success(`欢迎，${values.username}`);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <Card className="login-card" styles={{ body: { padding: '32px 24px' } }}>
        <Typography.Title level={4} className="login-title">
          H5 登录
        </Typography.Title>
        <div className="login-subtitle">欢迎回来，请登录您的账号</div>
        <Form<LoginFormValues>
          name="login"
          size="large"
          initialValues={{ remember: true }}
          onFinish={handleFinish}
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input prefix={<UserOutlined />} placeholder="用户名" />
          </Form.Item>
          <Form.Item
            name="password"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="密码" />
          </Form.Item>
          <Form.Item name="remember" valuePropName="checked">
            <Checkbox>记住我</Checkbox>
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block loading={loading}>
              登录
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
