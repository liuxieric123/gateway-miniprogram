// pages/temp-gate/temp-gate.js
// 临时用户通过分享链接进入的开关门页面
Page({
  data: {
    // 页面状态: 'checking' | 'valid' | 'invalid'
    status: 'checking',
    // 令牌信息
    token: '',
    remainSeconds: 0,
    remainTimeStr: '',
    // 倒计时 timer
    timer: null,
    // 加载状态
    isLoading: false,
    // 按钮冷却中（2s 内禁止重复点击）
    cooldown: false,
  },

  onLoad(options) {
    const token = options.token || '';
    if (!token) {
      this.setData({ status: 'invalid' });
      return;
    }

    this.setData({ token });
    this.validateToken(token);
  },

  onUnload() {
    if (this.data.timer) {
      clearInterval(this.data.timer);
    }
    if (this.cooldownTimer) {
      clearTimeout(this.cooldownTimer);
    }
  },

  // ============================================
  // 验证临时令牌
  // ============================================
  validateToken(token) {
    wx.cloud.callFunction({
      name: 'gateFunctions',
      data: { type: 'checkTempToken', token }
    }).then(res => {
      const result = res.result;
      if (result.valid) {
        this.setData({
          status: 'valid',
          remainSeconds: result.remainSeconds,
          remainTimeStr: this.formatRemainTime(result.remainSeconds)
        });
        // 启动倒计时
        this.startCountdown();
      } else {
        this.setData({ status: 'invalid' });
        wx.showModal({
          title: '链接已失效',
          content: result.errMsg || '该临时链接已无法使用',
          showCancel: false,
          success: () => {
            wx.switchTab({ url: '/pages/index/index' });
          }
        });
      }
    }).catch(err => {
      console.error('令牌验证失败:', err);
      this.setData({ status: 'invalid' });
      wx.showModal({
        title: '验证失败',
        content: '网络错误，请稍后重试',
        showCancel: false
      });
    });
  },

  // ============================================
  // 倒计时
  // ============================================
  startCountdown() {
    const timer = setInterval(() => {
      const remain = this.data.remainSeconds - 1;
      if (remain <= 0) {
        clearInterval(timer);
        this.setData({
          status: 'invalid',
          remainSeconds: 0,
          remainTimeStr: '00:00:00'
        });
        wx.showModal({
          title: '链接已过期',
          content: '临时权限已失效',
          showCancel: false,
          success: () => {
            wx.switchTab({ url: '/pages/index/index' });
          }
        });
        return;
      }
      this.setData({
        remainSeconds: remain,
        remainTimeStr: this.formatRemainTime(remain)
      });
    }, 1000);
    this.setData({ timer });
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
  // 控制闸门
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
        action,
        tempToken: this.data.token
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
      wx.showModal({
        title: '操作失败',
        content: err.errMsg || '网络错误，请重试',
        showCancel: false
      });
    });
  },

  // ============================================
  // 格式化剩余时间
  // ============================================
  formatRemainTime(seconds) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    const pad = n => String(n).padStart(2, '0');
    return `${pad(h)}:${pad(m)}:${pad(s)}`;
  }
});
