// pages/admin/users/users.js
/**
 * 用户管理页面
 */

const app = getApp();
const logger = require('../../../utils/logger');

Page({

  /**
   * 页面的初始数据
   */
  data: {
    loading: true,
    users: [],
    selectedUsers: [],
    selectAll: false,
    searchKeyword: '',
    pagination: {
      page: 1,
      page_size: 20,
      total: 0,
      total_pages: 0
    }
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad(options) {
    this.loadUsers();
  },

  /**
   * 加载用户列表
   */
  loadUsers() {
    try {
      this.setData({ loading: true });
      const token = wx.getStorageSync('token');
      const { page, page_size } = this.data.pagination;

      wx.request({
        url: `${app.globalData.serverUrl}/admin/users?page=${page}&page_size=${page_size}&search=${this.data.searchKeyword}`,
        header: { 'Authorization': token ? `Bearer ${token}` : '' },
        success: (res) => {
          if (res.statusCode === 200 && res.data.status === 'success') {
            const data = res.data.data;
            this.setData({
              loading: false,
              users: data.users,
              pagination: data.pagination
            });
          } else {
            throw new Error(res.data.error || '加载失败');
          }
        },
        fail: (err) => {
          logger.error('加载用户列表失败', err);
          this.setData({ loading: false });
          wx.showToast({
            title: '加载失败',
            icon: 'none'
          });
        }
      });
    } catch (error) {
      logger.error('加载用户列表异常', error);
      this.setData({ loading: false });
    }
  },

  /**
   * 搜索输入
   */
  onSearchInput(e) {
    this.setData({
      searchKeyword: e.detail.value
    });
  },

  /**
   * 搜索用户
   */
  searchUsers() {
    this.setData({ pagination: { ...this.data.pagination, page: 1 } });
    this.loadUsers();
  },

  /**
   * 选择单个用户
   */
  onSelectUser(e) {
    const userId = e.currentTarget.dataset.id;
    const checked = e.detail.value;
    
    let selectedUsers = [...this.data.selectedUsers];
    
    if (checked) {
      if (!selectedUsers.includes(userId)) {
        selectedUsers.push(userId);
      }
    } else {
      selectedUsers = selectedUsers.filter(id => id !== userId);
    }
    
    this.setData({
      selectedUsers,
      selectAll: selectedUsers.length === this.data.users.length
    });
  },

  /**
   * 全选/取消全选
   */
  onSelectAll(e) {
    const checked = e.detail.value.includes(true);
    
    if (checked) {
      const allUserIds = this.data.users.map(u => u.id);
      this.setData({
        selectedUsers: allUserIds,
        selectAll: true
      });
    } else {
      this.setData({
        selectedUsers: [],
        selectAll: false
      });
    }
  },

  /**
   * 清除选择
   */
  clearSelection() {
    this.setData({
      selectedUsers: [],
      selectAll: false
    });
  },

  /**
   * 批量授予管理员权限
   */
  batchGrantAdmin() {
    if (this.data.selectedUsers.length === 0) {
      wx.showToast({ title: '请选择用户', icon: 'none' });
      return;
    }

    wx.showModal({
      title: '确认操作',
      content: `确定要授予 ${this.data.selectedUsers.length} 个用户管理员权限吗？`,
      success: (res) => {
        if (res.confirm) {
          this.performBatchAction('grant_admin');
        }
      }
    });
  },

  /**
   * 批量撤销管理员权限
   */
  batchRevokeAdmin() {
    if (this.data.selectedUsers.length === 0) {
      wx.showToast({ title: '请选择用户', icon: 'none' });
      return;
    }

    wx.showModal({
      title: '确认操作',
      content: `确定要撤销 ${this.data.selectedUsers.length} 个用户的管理员权限吗？`,
      success: (res) => {
        if (res.confirm) {
          this.performBatchAction('revoke_admin');
        }
      }
    });
  },

  /**
   * 批量导出数据
   */
  batchExport() {
    if (this.data.selectedUsers.length === 0) {
      wx.showToast({ title: '请选择用户', icon: 'none' });
      return;
    }

    wx.showModal({
      title: '导出数据',
      content: `确定要导出 ${this.data.selectedUsers.length} 个用户的数据吗？`,
      success: (res) => {
        if (res.confirm) {
          this.performBatchAction('export_data');
        }
      }
    });
  },

  /**
   * 批量发送通知
   */
  batchNotify() {
    if (this.data.selectedUsers.length === 0) {
      wx.showToast({ title: '请选择用户', icon: 'none' });
      return;
    }

    wx.showModal({
      title: '发送通知',
      editable: true,
      placeholderText: '请输入通知内容',
      success: (res) => {
        if (res.confirm && res.content) {
          this.sendBatchNotification(res.content);
        }
      }
    });
  },

  /**
   * 执行批量操作
   */
  performBatchAction(action) {
    const token = wx.getStorageSync('token');
    
    wx.showLoading({ title: '处理中...', mask: true });

    wx.request({
      url: `${app.globalData.serverUrl}/admin/users/batch-action`,
      method: 'POST',
      header: { 
        'Authorization': token ? `Bearer ${token}` : '',
        'Content-Type': 'application/json'
      },
      data: {
        user_ids: this.data.selectedUsers,
        action: action
      },
      success: (res) => {
        wx.hideLoading();
        if (res.statusCode === 200 && res.data.status === 'success') {
          wx.showToast({
            title: `操作成功！处理 ${res.data.processed} 个`,
            icon: 'success'
          });
          this.clearSelection();
          this.loadUsers();
        } else {
          wx.showToast({
            title: res.data.error || '操作失败',
            icon: 'none'
          });
        }
      },
      fail: (err) => {
        wx.hideLoading();
        logger.error('批量操作失败', err);
        wx.showToast({
          title: '操作失败',
          icon: 'none'
        });
      }
    });
  },

  /**
   * 发送批量通知
   */
  sendBatchNotification(message) {
    const token = wx.getStorageSync('token');
    
    wx.showLoading({ title: '发送中...', mask: true });

    wx.request({
      url: `${app.globalData.serverUrl}/admin/users/batch-notification`,
      method: 'POST',
      header: { 
        'Authorization': token ? `Bearer ${token}` : '',
        'Content-Type': 'application/json'
      },
      data: {
        user_ids: this.data.selectedUsers,
        title: '系统通知',
        message: message,
        type: 'system'
      },
      success: (res) => {
        wx.hideLoading();
        if (res.statusCode === 200 && res.data.status === 'success') {
          wx.showToast({
            title: `已发送给 ${res.data.target_count} 个用户`,
            icon: 'success'
          });
          this.clearSelection();
        } else {
          wx.showToast({
            title: res.data.error || '发送失败',
            icon: 'none'
          });
        }
      },
      fail: (err) => {
        wx.hideLoading();
        logger.error('发送通知失败', err);
        wx.showToast({
          title: '发送失败',
          icon: 'none'
        });
      }
    });
  },

  /**
   * 导出全部用户
   */
  exportAllUsers() {
    wx.showLoading({ title: '生成文件中...', mask: true });

    const token = wx.getStorageSync('token');
    const timestamp = new Date().getTime();

    // 下载 CSV 文件
    wx.downloadFile({
      url: `${app.globalData.serverUrl}/admin/export/users?format=csv`,
      header: { 'Authorization': token ? `Bearer ${token}` : '' },
      success: (res) => {
        wx.hideLoading();
        if (res.statusCode === 200) {
          // 打开文件
          wx.openDocument({
            filePath: res.tempFilePath,
            showMenu: true,
            success: () => {
              wx.showToast({
                title: '导出成功',
                icon: 'success'
              });
            }
          });
        } else {
          wx.showToast({
            title: '导出失败',
            icon: 'none'
          });
        }
      },
      fail: (err) => {
        wx.hideLoading();
        logger.error('导出失败', err);
        wx.showToast({
          title: '导出失败',
          icon: 'none'
        });
      }
    });
  },

  /**
   * 查看用户详情
   */
  viewUserDetail(e) {
    const userId = e.currentTarget.dataset.id;
    wx.navigateTo({
      url: `/pages/admin/user-detail/user-detail?id=${userId}`
    });
  },

  /**
   * 切换用户角色
   */
  toggleUserRole(e) {
    const userId = e.currentTarget.dataset.id;
    const action = e.currentTarget.dataset.action;
    const token = wx.getStorageSync('token');

    wx.showModal({
      title: '确认操作',
      content: `确定要${action === 'grant' ? '授予' : '撤销'}该用户的管理员权限吗？`,
      success: (res) => {
        if (res.confirm) {
          wx.showLoading({ title: '处理中...', mask: true });

          wx.request({
            url: `${app.globalData.serverUrl}/admin/users/${userId}/roles`,
            method: 'POST',
            header: { 
              'Authorization': token ? `Bearer ${token}` : '',
              'Content-Type': 'application/json'
            },
            data: {
              role: 'admin',
              action: action
            },
            success: (res) => {
              wx.hideLoading();
              if (res.statusCode === 200 && res.data.status === 'success') {
                wx.showToast({
                  title: '操作成功',
                  icon: 'success'
                });
                this.loadUsers();
              } else {
                wx.showToast({
                  title: res.data.error || '操作失败',
                  icon: 'none'
                });
              }
            },
            fail: (err) => {
              wx.hideLoading();
              logger.error('操作失败', err);
              wx.showToast({
                title: '操作失败',
                icon: 'none'
              });
            }
          });
        }
      }
    });
  },

  /**
   * 分页
   */
  prevPage() {
    if (this.data.pagination.page > 1) {
      this.setData({
        pagination: { ...this.data.pagination, page: this.data.pagination.page - 1 }
      });
      this.loadUsers();
    }
  },

  nextPage() {
    if (this.data.pagination.page < this.data.pagination.total_pages) {
      this.setData({
        pagination: { ...this.data.pagination, page: this.data.pagination.page + 1 }
      });
      this.loadUsers();
    }
  },

  /**
   * 格式化日期
   */
  formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${month}-${day}`;
  },

  /**
   * 页面相关事件处理函数--监听用户下拉动作
   */
  onPullDownRefresh() {
    this.loadUsers();
    wx.stopPullDownRefresh();
  },

  /**
   * 用户点击右上角分享
   */
  onShareAppMessage() {
    return {
      title: '用户管理 - 品牌 AI 诊断系统',
      path: '/pages/admin/users/users'
    };
  }
});
