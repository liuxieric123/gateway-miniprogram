// pages/admin/admin.js
Page({
  data: {
    isLoading: true,
    isSuperAdmin: false,
    currentTab: 'users',
    users: [],
    logs: [],
    tokens: [],
    showUserModal: false,
    modalMode: 'add', // 'add' | 'edit'
    userForm: {
      openid: '',
      nickname: '',
      role: 'user'
    },
    editingUserId: '',
    roleOptions: [
      { value: 'user', label: '普通用户 (user)' },
      { value: 'admin', label: '管理员 (admin)' },
      { value: 'super_admin', label: '超级管理员 (super_admin)' }
    ],
    roleIndex: 0,
    // 滚动通知表单
    noticeForm: {
      content: '',
      enabled: false
    },
    noticeSaving: false
  },

  onLoad() {
    this.checkPermission();
  },

  onPullDownRefresh() {
    if (!this.data.isSuperAdmin) {
      wx.stopPullDownRefresh();
      return;
    }
    this.loadCurrentTabData().finally(() => {
      wx.stopPullDownRefresh();
    });
  },

  // 校验当前用户是否为超级管理员
  checkPermission() {
    wx.cloud.callFunction({
      name: 'gateFunctions',
      data: { type: 'getUserPermission' }
    }).then(res => {
      const result = res.result || {};
      const isSuperAdmin = result.hasPermission && result.userInfo?.role === 'super_admin';
      this.setData({
        isLoading: false,
        isSuperAdmin
      });
      if (isSuperAdmin) {
        this.loadCurrentTabData();
      }
    }).catch(err => {
      console.error('权限校验失败:', err);
      this.setData({
        isLoading: false,
        isSuperAdmin: false
      });
    });
  },

  // 返回首页
  goBack() {
    const pages = getCurrentPages();
    if (pages.length > 1) {
      wx.navigateBack();
    } else {
      wx.redirectTo({
        url: '/pages/index/index'
      });
    }
  },

  // 切换 Tab
  switchTab(e) {
    console.log('[switchTab] 点击:', e.currentTarget.dataset.tab);
    const tab = e.currentTarget.dataset.tab;
    if (tab === this.data.currentTab) return;
    this.setData({ currentTab: tab }, () => {
      this.loadCurrentTabData();
    });
  },

  // 根据当前 Tab 加载对应数据
  loadCurrentTabData() {
    const { currentTab } = this.data;
    if (currentTab === 'users') return this.loadUsers();
    if (currentTab === 'logs') return this.loadLogs();
    if (currentTab === 'tokens') return this.loadTokens();
    if (currentTab === 'notice') return this.loadNotice();
    return Promise.resolve();
  },

  // 加载滚动通知
  loadNotice() {
    return wx.cloud.callFunction({
      name: 'gateFunctions',
      data: { type: 'getNotice' }
    }).then(res => {
      const result = res.result || {};
      const data = (result.success && result.data) || { content: '', enabled: false };
      this.setData({
        noticeForm: {
          content: data.content || '',
          enabled: !!data.enabled
        }
      });
    }).catch(err => {
      console.error('加载通知失败:', err);
      wx.showToast({ title: '加载通知失败', icon: 'none' });
    });
  },

  // 通知内容输入
  onNoticeInput(e) {
    this.setData({ 'noticeForm.content': e.detail.value });
  },

  // 通知开关切换
  onNoticeToggle(e) {
    this.setData({ 'noticeForm.enabled': e.detail.value });
  },

  // 保存滚动通知
  saveNotice() {
    const { noticeForm, noticeSaving } = this.data;
    if (noticeSaving) return;

    const content = (noticeForm.content || '').trim();
    if (noticeForm.enabled && !content) {
      wx.showToast({ title: '开启前请先填写通知内容', icon: 'none' });
      return;
    }

    this.setData({ noticeSaving: true });
    wx.cloud.callFunction({
      name: 'gateFunctions',
      data: {
        type: 'setNotice',
        content,
        enabled: noticeForm.enabled
      }
    }).then(res => {
      const result = res.result || {};
      this.setData({ noticeSaving: false });
      if (!result.success) {
        wx.showToast({ title: result.errMsg || '保存失败', icon: 'none' });
        return;
      }
      wx.showToast({ title: '保存成功', icon: 'success' });
    }).catch(err => {
      console.error('保存通知失败:', err);
      this.setData({ noticeSaving: false });
      wx.showToast({ title: '保存失败', icon: 'none' });
    });
  },

  // 加载授权用户
  loadUsers() {
    return wx.cloud.callFunction({
      name: 'gateFunctions',
      data: { type: 'getAuthorizedUsers' }
    }).then(res => {
      const result = res.result || {};
      if (!result.success) {
        wx.showToast({ title: result.errMsg || '加载失败', icon: 'none' });
        return;
      }
      const users = (result.data || []).map(item => ({
        ...item,
        createTimeText: this.formatTime(item.createTime),
        lastSeenText: this.formatTime(item.lastSeen)
      }));
      this.setData({ users });
    }).catch(err => {
      console.error('加载用户失败:', err);
      wx.showToast({ title: '加载用户失败', icon: 'none' });
    });
  },

  // 加载操作日志
  loadLogs() {
    return wx.cloud.callFunction({
      name: 'gateFunctions',
      data: { type: 'getAdminGateLogs', limit: 100 }
    }).then(res => {
      const result = res.result || {};
      if (!result.success) {
        wx.showToast({ title: result.errMsg || '加载失败', icon: 'none' });
        return;
      }
      const logs = (result.data || []).map(item => ({
        ...item,
        createTimeText: this.formatTime(item.createTime)
      }));
      this.setData({ logs });
    }).catch(err => {
      console.error('加载日志失败:', err);
      wx.showToast({ title: '加载日志失败', icon: 'none' });
    });
  },

  // 加载临时链接
  loadTokens() {
    return wx.cloud.callFunction({
      name: 'gateFunctions',
      data: { type: 'getTempTokens', limit: 100 }
    }).then(res => {
      const result = res.result || {};
      if (!result.success) {
        wx.showToast({ title: result.errMsg || '加载失败', icon: 'none' });
        return;
      }
      const tokens = (result.data || []).map(item => {
        const statusText = this.getTokenStatusText(item);
        return {
          ...item,
          statusText,
          createTimeText: this.formatTime(item.createTime),
          expireTimeText: this.formatTime(item.expireAt),
          usedTimeText: item.usedTime ? this.formatTime(item.usedTime) : ''
        };
      });
      this.setData({ tokens });
    }).catch(err => {
      console.error('加载临时链接失败:', err);
      wx.showToast({ title: '加载临时链接失败', icon: 'none' });
    });
  },

  // 获取临时链接状态文本
  getTokenStatusText(item) {
    if (item.used) return '已使用';
    if (item.status === 'expired') return '已过期';
    if (item.status === 'active') return '有效';
    return item.status || '未知';
  },

  // 显示新增用户弹窗
  showAddUserModal() {
    console.log('[showAddUserModal] 打开新增弹窗');
    this.setData({
      showUserModal: true,
      modalMode: 'add',
      userForm: { openid: '', nickname: '', role: 'user' },
      editingUserId: '',
      roleIndex: 0
    });
  },

  // 显示编辑用户弹窗
  showEditUserModal(e) {
    console.log('[showEditUserModal] 点击编辑:', e.currentTarget.dataset.id);
    const id = e.currentTarget.dataset.id;
    const user = this.data.users.find(item => item._id === id);
    if (!user) return;

    const roleIndex = this.data.roleOptions.findIndex(item => item.value === user.role);
    this.setData({
      showUserModal: true,
      modalMode: 'edit',
      userForm: {
        openid: user.openid,
        nickname: user.nickname || '',
        role: user.role || 'user'
      },
      editingUserId: id,
      roleIndex: roleIndex >= 0 ? roleIndex : 0
    });
  },

  // 隐藏弹窗
  hideUserModal() {
    console.log('[hideUserModal] 关闭弹窗');
    this.setData({ showUserModal: false });
  },

  // 阻止冒泡
  stopPropagation() {
    // 空函数，用于 catchtap
  },

  // 表单输入
  onUserFormInput(e) {
    const field = e.currentTarget.dataset.field;
    const value = e.detail.value;
    this.setData({
      [`userForm.${field}`]: value
    });
  },

  // 角色选择
  onRoleChange(e) {
    const index = parseInt(e.detail.value, 10);
    const role = this.data.roleOptions[index].value;
    this.setData({
      roleIndex: index,
      'userForm.role': role
    });
  },

  // 提交用户表单
  submitUserForm() {
    console.log('[submitUserForm] 提交表单:', this.data.userForm, 'roleIndex:', this.data.roleIndex);
    const { modalMode, userForm, editingUserId, roleOptions, roleIndex } = this.data;
    const role = roleOptions[roleIndex].value;

    if (!userForm.nickname.trim()) {
      wx.showToast({ title: '请输入昵称', icon: 'none' });
      return;
    }

    if (modalMode === 'add') {
      if (!userForm.openid.trim()) {
        wx.showToast({ title: '请输入 openid', icon: 'none' });
        return;
      }
      wx.cloud.callFunction({
        name: 'gateFunctions',
        data: {
          type: 'addAuthorizedUser',
          targetOpenid: userForm.openid.trim(),
          nickname: userForm.nickname.trim(),
          role
        }
      }).then(res => {
        const result = res.result || {};
        if (!result.success) {
          wx.showToast({ title: result.errMsg || '添加失败', icon: 'none' });
          return;
        }
        wx.showToast({ title: '添加成功', icon: 'success' });
        this.hideUserModal();
        this.loadUsers();
      }).catch(err => {
        console.error('添加用户失败:', err);
        wx.showToast({ title: '添加失败', icon: 'none' });
      });
    } else {
      wx.cloud.callFunction({
        name: 'gateFunctions',
        data: {
          type: 'updateAuthorizedUser',
          _id: editingUserId,
          nickname: userForm.nickname.trim(),
          role
        }
      }).then(res => {
        const result = res.result || {};
        if (!result.success) {
          wx.showToast({ title: result.errMsg || '更新失败', icon: 'none' });
          return;
        }
        wx.showToast({ title: '更新成功', icon: 'success' });
        this.hideUserModal();
        this.loadUsers();
      }).catch(err => {
        console.error('更新用户失败:', err);
        wx.showToast({ title: '更新失败', icon: 'none' });
      });
    }
  },

  // 删除用户
  deleteUser(e) {
    console.log('[deleteUser] 点击删除:', e.currentTarget.dataset.id);
    const id = e.currentTarget.dataset.id;
    wx.showModal({
      title: '确认删除',
      content: '删除后该用户将失去所有权限，是否继续？',
      confirmColor: '#D32F2F',
      success: (res) => {
        if (!res.confirm) return;
        wx.cloud.callFunction({
          name: 'gateFunctions',
          data: { type: 'deleteAuthorizedUser', _id: id }
        }).then(res => {
          const result = res.result || {};
          if (!result.success) {
            wx.showToast({ title: result.errMsg || '删除失败', icon: 'none' });
            return;
          }
          wx.showToast({ title: '删除成功', icon: 'success' });
          this.loadUsers();
        }).catch(err => {
          console.error('删除用户失败:', err);
          wx.showToast({ title: '删除失败', icon: 'none' });
        });
      }
    });
  },

  // 格式化时间
  formatTime(date) {
    if (!date) return '-';
    let d;
    if (date instanceof Date) {
      d = date;
    } else if (typeof date === 'object' && date.$date) {
      // 云函数返回的 serverDate 在小程序端可能解析为这种结构
      d = new Date(date.$date);
    } else {
      d = new Date(date);
    }
    if (isNaN(d.getTime())) return '-';

    const pad = (n) => (n < 10 ? '0' + n : n);
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }
});
