// pages/gate/gate.js
Page({
  data: {
    // 权限状态
    hasPermission: false,
    openid: '',
    // 加载状态
    isLoading: false,
    // 按钮冷却中（2s 内禁止重复点击）
    cooldown: false,
    // 是否显示临时链接弹窗
    showTempModal: false,
    // 生成的临时链接
    tempLink: '',
    // 临时链接过期时间
    tempExpireTime: '',
    // 自定义导航栏高度
    statusBarHeight: 20,
    navHeight: 64,
  },

  onLoad() {
    const sysInfo = wx.getSystemInfoSync();
    this.setData({
      statusBarHeight: sysInfo.statusBarHeight,
      navHeight: sysInfo.statusBarHeight + 44,
    });
    this.checkUserPermission();
  },

  onUnload() {
    if (this.cooldownTimer) {
      clearTimeout(this.cooldownTimer);
    }
  },

  goBack() {
    wx.navigateBack();
  },

  // ============================================
  // 检查用户权限
  // ============================================
  checkUserPermission() {
    wx.showLoading({ title: '检查权限...' });
    console.log('【gate】开始调用云函数 getUserPermission...');

    wx.cloud.callFunction({
      name: 'gateFunctions',
      data: { type: 'getUserPermission' }
    }).then(res => {
      wx.hideLoading();
      console.log('【gate】云函数调用成功，完整返回:', res);
      console.log('【gate】res.result:', res.result);

      const result = res.result;
      if (!result) {
        console.error('【gate】res.result 为空！');
        this.setData({ hasPermission: false, openid: 'result为空' });
        return;
      }

      console.log('【gate】openid:', result.openid);
      console.log('【gate】hasPermission:', result.hasPermission);
      console.log('【gate】userInfo:', result.userInfo);
      console.log('【gate】errMsg:', result.errMsg);

      if (result.hasPermission) {
        this.setData({
          hasPermission: true,
          openid: result.openid || ''
        });
      } else {
        this.setData({
          hasPermission: false,
          openid: result.openid || ('无openid，errMsg:' + (result.errMsg || '无'))
        });
      }
    }).catch(err => {
      wx.hideLoading();
      console.error('【gate】云函数调用失败(catch):', err);
      console.error('【gate】错误详情:', JSON.stringify(err));
      this.setData({
        hasPermission: false,
        openid: '调用失败: ' + (err.errMsg || err.message || JSON.stringify(err))
      });
      wx.showToast({ title: '云函数调用失败', icon: 'none' });
    });
  },

  // ============================================
  // 开门
  // ============================================
  openGate() {
    this.controlGate('open');
  },

  // ============================================
  // 关门
  // ============================================
  closeGate() {
    this.controlGate('close');
  },

  // ============================================
  // 控制闸门核心方法
  // ============================================
  controlGate(action) {
    if (this.data.isLoading || this.data.cooldown) return;

    // 进入 2 秒冷却，防止快速重复点击
    this.setData({ cooldown: true });
    this.cooldownTimer = setTimeout(() => {
      this.setData({ cooldown: false });
    }, 2000);

    this.doControlGate(action);
  },

  doControlGate(action) {
    this.setData({ isLoading: true });
    wx.showLoading({ title: '发送指令...' });

    wx.cloud.callFunction({
      name: 'gateFunctions',
      data: {
        type: 'gateControl',
        action
      }
    }).then(res => {
      wx.hideLoading();
      this.setData({ isLoading: false });

      const result = res.result;
      if (result.success) {
        wx.showToast({ title: result.message, icon: 'success' });
      } else {
        wx.showModal({
          title: '操作失败',
          content: result.errMsg || '未知错误',
          showCancel: false
        });
      }
    }).catch(err => {
      wx.hideLoading();
      this.setData({ isLoading: false });
      console.error('闸门控制失败:', err);
      wx.showModal({
        title: '操作失败',
        content: err.errMsg || '网络错误，请重试',
        showCancel: false
      });
    });
  },

  // ============================================
  // 生成临时链接
  // ============================================
  generateTempLink() {
    wx.showLoading({ title: '生成中...' });

    wx.cloud.callFunction({
      name: 'gateFunctions',
      data: { type: 'createTempToken' }
    }).then(res => {
      wx.hideLoading();
      const result = res.result;

      if (result.success) {
        const token = result.token;
        const link = `pages/temp-gate/temp-gate?token=${token}`;
        const expireDate = new Date(result.expireAt);
        const expireStr = `${expireDate.getHours()}:${String(expireDate.getMinutes()).padStart(2, '0')}`;

        this.setData({
          showTempModal: true,
          tempLink: link,
          tempExpireTime: expireStr
        });
      } else {
        wx.showModal({
          title: '生成失败',
          content: result.errMsg || '未知错误',
          showCancel: false
        });
      }
    }).catch(err => {
      wx.hideLoading();
      console.error('生成临时链接失败:', err);
      wx.showModal({
        title: '生成失败',
        content: err.errMsg || '网络错误，请重试',
        showCancel: false
      });
    });
  },

  // ============================================
  // 关闭临时链接弹窗
  // ============================================
  closeTempModal() {
    this.setData({ showTempModal: false });
  },

  onShareAppMessage() {
    return {
      title: '临时开关门',
      path: '/' + this.data.tempLink,
      imageUrl: ''
    };
  }
});
