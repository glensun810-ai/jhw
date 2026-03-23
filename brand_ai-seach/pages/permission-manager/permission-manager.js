/**
 * 权限管理页 - P1 级空缺修复
 * 
 * 功能:
 * 1. 查看用户权限
 * 2. 查看所有权限列表
 * 3. 查看所有角色列表
 * 4. 授予权限 (管理员)
 * 5. 分配角色 (管理员)
 */

const app = getApp();
const logger = require('../../utils/logger');

Page({
  data: {
    loading: true,
    error: null,
    userId: '',
    
    // 当前用户权限
    permissionsData: null,
    
    // 所有权限列表
    allPermissions: [],
    
    // 所有角色列表
    allRoles: [],
    
    // 授予权限表单
    grantForm: {
      userId: '',
      permissionIndex: -1,
      reason: '',
      expiresDays: ''
    }
  },

  onLoad() {
    // 获取当前用户 ID
    const userId = app.globalData.userOpenid || this.getQueryParam('user_id');
    
    if (userId) {
      this.setData({ userId });
      this.loadPermissions(userId);
    } else {
      this.setData({
        loading: false,
        error: '未找到用户 ID'
      });
    }
  },

  /**
   * 加载权限数据
   */
  async loadPermissions(userId) {
    try {
      this.setData({ loading: true, error: null });

      // 并行加载三个 API，使用 Promise.allSettled 避免单个失败影响全部
      const [permissionsRes, allPermsRes, allRolesRes] = await Promise.all([
        this.fetchUserPermissions(userId).catch(err => {
          logger.warn('获取用户权限失败，继续加载其他数据', err);
          return null;
        }),
        this.fetchAllPermissions().catch(err => {
          logger.warn('获取权限列表失败，继续加载其他数据', err);
          return null;
        }),
        this.fetchAllRoles().catch(err => {
          logger.warn('获取角色列表失败，继续加载其他数据', err);
          return null;
        })
      ]);

      this.setData({
        loading: false,
        permissionsData: permissionsRes,
        allPermissions: allPermsRes,
        allRoles: allRolesRes
      });

      logger.info('Permissions loaded successfully', { userId });
    } catch (error) {
      logger.error('Failed to load permissions', error);
      this.setData({
        loading: false,
        error: error.message || '加载失败，请重试'
      });
    }
  },

  /**
   * 获取用户权限
   */
  fetchUserPermissions(userId) {
    return new Promise((resolve, reject) => {
      wx.request({
        url: `${app.globalData.apiBaseUrl}/api/user/permissions`,
        method: 'GET',
        data: { user_id: userId },
        timeout: 10000,
        success: (res) => {
          if (res.data && res.data.success) {
            resolve(res.data.data);
          } else {
            reject(new Error(res.data?.error || '获取权限失败'));
          }
        },
        fail: (error) => {
          reject(new Error('网络请求失败'));
        }
      });
    });
  },

  /**
   * 获取所有权限
   */
  fetchAllPermissions() {
    return new Promise((resolve, reject) => {
      wx.request({
        url: `${app.globalData.apiBaseUrl}/api/user/permissions/all`,
        method: 'GET',
        timeout: 10000,
        success: (res) => {
          if (res.data && res.data.success) {
            resolve(res.data.data);
          } else {
            reject(new Error('获取权限列表失败'));
          }
        },
        fail: (error) => {
          reject(new Error('网络请求失败'));
        }
      });
    });
  },

  /**
   * 获取所有角色
   */
  fetchAllRoles() {
    return new Promise((resolve, reject) => {
      wx.request({
        url: `${app.globalData.apiBaseUrl}/api/user/roles`,
        method: 'GET',
        timeout: 10000,
        success: (res) => {
          if (res.data && res.data.success) {
            resolve(res.data.data);
          } else {
            reject(new Error('获取角色列表失败'));
          }
        },
        fail: (error) => {
          reject(new Error('网络请求失败'));
        }
      });
    });
  },

  /**
   * 检查是否拥有权限
   */
  hasPermission(permissionId) {
    const { permissionsData } = this.data;
    if (!permissionsData) return false;
    
    return permissionsData.permissions.some(p => p.id === permissionId);
  },

  /**
   * 检查是否拥有角色
   */
  hasRole(roleName) {
    const { permissionsData } = this.data;
    if (!permissionsData) return false;
    
    return permissionsData.role_names.includes(roleName);
  },

  /**
   * 表单输入处理
   */
  onGrantUserIdInput(event) {
    this.setData({ 'grantForm.userId': event.detail.value });
  },

  onGrantPermissionChange(event) {
    this.setData({ 'grantForm.permissionIndex': Number(event.detail.value) });
  },

  onGrantReasonInput(event) {
    this.setData({ 'grantForm.reason': event.detail.value });
  },

  onGrantExpiresInput(event) {
    this.setData({ 'grantForm.expiresDays': event.detail.value });
  },

  /**
   * 授予权限
   */
  async onGrantPermission() {
    const { grantForm, allPermissions } = this.data;
    
    // 验证表单
    if (!grantForm.userId) {
      wx.showToast({ title: '请输入用户 ID', icon: 'none' });
      return;
    }
    
    if (grantForm.permissionIndex < 0) {
      wx.showToast({ title: '请选择权限', icon: 'none' });
      return;
    }
    
    const permission = allPermissions[grantForm.permissionIndex];
    
    try {
      wx.showLoading({ title: '授予中...', mask: true });
      
      const response = await this.grantPermission({
        user_id: grantForm.userId,
        permission_id: permission.id,
        reason: grantForm.reason,
        expires_days: grantForm.expiresDays ? Number(grantForm.expiresDays) : undefined
      });
      
      wx.hideLoading();
      
      if (response.success) {
        wx.showToast({ title: '授予成功', icon: 'success' });
        
        // 清空表单
        this.setData({
          'grantForm.userId': '',
          'grantForm.permissionIndex': -1,
          'grantForm.reason': '',
          'grantForm.expiresDays': ''
        });
        
        // 重新加载权限
        if (grantForm.userId === this.data.userId) {
          this.loadPermissions(this.data.userId);
        }
      } else {
        wx.showToast({ title: response.error || '授予失败', icon: 'none' });
      }
    } catch (error) {
      wx.hideLoading();
      wx.showToast({ title: error.message || '授予失败', icon: 'none' });
    }
  },

  /**
   * 授予权限 API 调用
   */
  grantPermission(data) {
    return new Promise((resolve, reject) => {
      wx.request({
        url: `${app.globalData.apiBaseUrl}/api/user/permission/grant`,
        method: 'POST',
        data: data,
        header: {
          'X-User-Id': this.data.userId
        },
        timeout: 10000,
        success: (res) => {
          resolve(res.data);
        },
        fail: (error) => {
          reject(new Error('网络请求失败'));
        }
      });
    });
  },

  /**
   * 分配角色
   */
  onAssignRole(event) {
    const role = event.currentTarget.dataset.role;
    const userId = this.data.userId;
    
    wx.showModal({
      title: '分配角色',
      content: `确定要将角色 "${role.name}" 分配给用户吗？`,
      success: (res) => {
        if (res.confirm) {
          this.assignRoleToUser(userId, role);
        }
      }
    });
  },

  /**
   * 执行角色分配 API 调用
   */
  assignRoleToUser(userId, role) {
    wx.showLoading({ title: '分配中...' });
    
    wx.request({
      url: `${app.globalData.apiBaseUrl}/api/user/role/assign`,
      method: 'POST',
      data: {
        userId: userId,
        roleId: role.id,
        roleName: role.name
      },
      timeout: 10000,
      success: (res) => {
        wx.hideLoading();
        if (res.statusCode === 200 && res.data) {
          wx.showToast({
            title: '分配成功',
            icon: 'success'
          });
          
          // 刷新用户权限列表
          this.loadPermissions(userId);
        } else {
          wx.showToast({
            title: res.data?.message || '分配失败',
            icon: 'none'
          });
        }
      },
      fail: (err) => {
        wx.hideLoading();
        logger.error('分配角色失败', err);
        wx.showToast({
          title: '网络错误，请重试',
          icon: 'none'
        });
      }
    });
  },

  /**
   * 获取 URL 参数
   */
  getQueryParam(name) {
    const pages = getCurrentPages();
    const currentPage = pages[pages.length - 1];
    const options = currentPage.options || {};
    return options[name];
  },

  /**
   * 重试
   */
  retry() {
    this.loadPermissions(this.data.userId);
  },

  /**
   * 页面分享
   */
  onShareAppMessage() {
    return {
      title: '权限管理',
      path: `/pages/permission-manager/permission-manager?user_id=${this.data.userId}`
    };
  }
});
