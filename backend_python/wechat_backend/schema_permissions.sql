-- 权限管理数据库表结构
-- P1 级空缺修复 - 后端支持
-- 执行：sqlite3 database.db < schema_permissions.sql

-- 权限表
CREATE TABLE IF NOT EXISTS permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 角色表
CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 用户角色关联表
CREATE TABLE IF NOT EXISTS user_roles (
    user_id TEXT NOT NULL,
    role_id INTEGER NOT NULL,
    granted_by TEXT,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
);

-- 角色权限关联表
CREATE TABLE IF NOT EXISTS role_permissions (
    role_id INTEGER NOT NULL,
    permission_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (role_id, permission_id),
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
);

-- 权限变更日志表
CREATE TABLE IF NOT EXISTS permission_change_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    action TEXT NOT NULL,  -- grant/revoke
    permission_id INTEGER,
    role_id INTEGER,
    changed_by TEXT NOT NULL,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 初始化默认权限
INSERT OR IGNORE INTO permissions (name, description) VALUES
    ('view_report', '查看报告'),
    ('export_data', '导出数据'),
    ('manage_users', '管理用户'),
    ('delete_data', '删除数据'),
    ('admin_access', '管理员权限'),
    ('view_public', '查看公共数据'),
    ('edit_own', '编辑自己的数据'),
    ('share_report', '分享报告');

-- 初始化默认角色
INSERT OR IGNORE INTO roles (name, description) VALUES
    ('guest', '访客 - 仅查看公共数据'),
    ('user', '普通用户 - 基础功能'),
    ('premium', '高级用户 - 导出和分享'),
    ('admin', '管理员 - 全部权限');

-- 初始化角色权限关联
-- guest 角色：仅查看公共数据
INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p 
WHERE r.name = 'guest' AND p.name = 'view_public';

-- user 角色：基础功能
INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p 
WHERE r.name = 'user' AND p.name IN ('view_report', 'view_public', 'edit_own');

-- premium 角色：导出和分享
INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p 
WHERE r.name = 'premium' AND p.name IN ('view_report', 'view_public', 'edit_own', 'export_data', 'share_report');

-- admin 角色：全部权限
INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p 
WHERE r.name = 'admin';

-- 创建索引加速查询
CREATE INDEX IF NOT EXISTS idx_user_roles_user ON user_roles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_role ON user_roles(role_id);
CREATE INDEX IF NOT EXISTS idx_role_permissions_role ON role_permissions(role_id);
CREATE INDEX IF NOT EXISTS idx_role_permissions_permission ON role_permissions(permission_id);
CREATE INDEX IF NOT EXISTS idx_permission_log_user ON permission_change_log(user_id);
