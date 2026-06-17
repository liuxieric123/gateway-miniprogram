const cloud = require("wx-server-sdk");
cloud.init({
  env: cloud.DYNAMIC_CURRENT_ENV,
});

const db = cloud.database();
const _ = db.command;

// 集合名称
const COLLECTION_GATE_LOGS = "gate_logs";
const COLLECTION_AUTH_USERS = "authorized_users";
const COLLECTION_TEMP_TOKENS = "temp_tokens";

// ============================================
// 生成随机 token
// ============================================
const generateToken = () => {
  return (
    Date.now().toString(36) +
    Math.random().toString(36).substr(2, 10)
  ).toUpperCase();
};

// ============================================
// 权限检查（已授权用户）
// ============================================
const checkPermission = async () => {
  const wxContext = cloud.getWXContext();
  const openid = wxContext.OPENID;

  if (!openid) {
    return { hasPermission: false, errMsg: "无法获取用户身份" };
  }

  try {
    const res = await db
      .collection(COLLECTION_AUTH_USERS)
      .where({ openid })
      .get();

    if (res.data.length > 0) {
      return {
        hasPermission: true,
        openid,
        userInfo: res.data[0],
      };
    }

    return { hasPermission: false, openid, errMsg: "您没有操作闸门的权限" };
  } catch (e) {
    console.error("权限检查失败:", e);
    return { hasPermission: false, errMsg: "权限检查失败: " + e.message };
  }
};

// ============================================
// 检查临时令牌
// ============================================
const checkTempToken = async (event) => {
  const { token } = event;

  if (!token) {
    return { valid: false, errMsg: "缺少令牌" };
  }

  try {
    const res = await db
      .collection(COLLECTION_TEMP_TOKENS)
      .where({ token })
      .get();

    if (res.data.length === 0) {
      return { valid: false, errMsg: "无效的令牌" };
    }

    const tokenData = res.data[0];

    if (tokenData.status !== "active") {
      return { valid: false, errMsg: "令牌已失效" };
    }

    if (tokenData.used === true) {
      return { valid: false, errMsg: "该链接已被使用，无法再次操作" };
    }

    const now = new Date();
    const expireAt = tokenData.expireAt instanceof Date
      ? tokenData.expireAt
      : new Date(tokenData.expireAt);

    if (now > expireAt) {
      // 自动标记为过期
      await db
        .collection(COLLECTION_TEMP_TOKENS)
        .doc(tokenData._id)
        .update({ data: { status: "expired" } });

      return { valid: false, errMsg: "令牌已过期" };
    }

    // 计算剩余时间（秒）
    const remainSeconds = Math.floor((expireAt - now) / 1000);

    return {
      valid: true,
      token: tokenData.token,
      createdBy: tokenData.createdBy,
      remainSeconds,
    };
  } catch (e) {
    console.error("令牌检查失败:", e);
    return { valid: false, errMsg: "令牌检查失败: " + e.message };
  }
};

// ============================================
// 创建临时令牌（1小时有效期）
// ============================================
const createTempToken = async (event) => {
  // 1. 检查调用者是否为授权用户
  const perm = await checkPermission();
  if (!perm.hasPermission) {
    return { success: false, errMsg: "您没有创建临时令牌的权限" };
  }

  // 2. 检查当前有效 token 数量
  // 超级管理员(super_admin)不限数量，普通管理员最多3个
  const userRole = perm.userInfo?.role || "admin";
  if (userRole !== "super_admin") {
    try {
      const activeTokens = await db
        .collection(COLLECTION_TEMP_TOKENS)
        .where({
          createdBy: perm.openid,
          status: "active",
          used: false,
          expireAt: _.gt(new Date()),
        })
        .count();

      if (activeTokens.total >= 3) {
        return {
          success: false,
          errMsg: `您已有 ${activeTokens.total} 个有效的临时链接，请先等待它们过期或被使用后再创建新的`,
        };
      }
    } catch (e) {
      console.error("统计有效令牌失败:", e);
    }
  }

  const token = generateToken();
  const now = new Date();
  const expireAt = new Date(now.getTime() + 60 * 60 * 1000); // 1小时后

  try {
    await db.collection(COLLECTION_TEMP_TOKENS).add({
      data: {
        token,
        createdBy: perm.openid,
        creatorName: perm.userInfo?.nickname || "管理员",
        status: "active",
        used: false,
        createTime: db.serverDate(),
        expireAt: expireAt,
      },
    });

    return {
      success: true,
      token,
      expireAt: expireAt.getTime(),
    };
  } catch (e) {
    console.error("创建令牌失败:", e);
    return { success: false, errMsg: "创建令牌失败: " + e.message };
  }
};

// ============================================
// 闸门控制（支持临时令牌）
// ============================================
const gateControl = async (event) => {
  const { action, tempToken } = event;
  const validActions = ["open", "close"];

  if (!validActions.includes(action)) {
    return { success: false, errMsg: "无效的操作指令" };
  }

  let operatorInfo = null;

  // 1. 权限验证
  if (tempToken) {
    // 使用临时令牌验证
    const tokenCheck = await checkTempToken({ token: tempToken });
    if (!tokenCheck.valid) {
      return { success: false, errMsg: tokenCheck.errMsg };
    }
    operatorInfo = {
      type: "temp",
      openid: "temp_" + tempToken,
      nickname: "临时访客",
      token: tempToken,
    };
  } else {
    // 使用常规权限验证
    const perm = await checkPermission();
    if (!perm.hasPermission) {
      return { success: false, errMsg: perm.errMsg };
    }
    operatorInfo = {
      type: "normal",
      openid: perm.openid,
      nickname: perm.userInfo?.nickname || "未知用户",
    };
  }

  // 2. 调用 REST API 控制闸门
  // ============================================================
  const http = require("http");
  const API_HOST = "139.155.148.224";
  const API_PORT = 8080;
  const API_KEY = "wechat_eric_012345";
  const apiPath = action === "open" ? "/api/v1/door/open" : "/api/v1/door/close";

  const callDoorApi = () => {
    return new Promise((resolve, reject) => {
      const req = http.request(
        {
          hostname: API_HOST,
          port: API_PORT,
          path: apiPath,
          method: "POST",
          headers: {
            "X-API-Key": API_KEY,
          },
          timeout: 10000, // 10秒超时
        },
        (res) => {
          let data = "";
          res.on("data", (chunk) => {
            data += chunk;
          });
          res.on("end", () => {
            if (res.statusCode >= 200 && res.statusCode < 300) {
              resolve({ success: true, message: "指令已发送", data });
            } else {
              reject(new Error(`API 返回 ${res.statusCode}: ${data}`));
            }
          });
        }
      );

      req.on("error", (err) => {
        reject(err);
      });

      req.on("timeout", () => {
        req.destroy();
        reject(new Error("请求超时"));
      });

      req.end();
    });
  };

  let esphomeResult;
  try {
    esphomeResult = await callDoorApi();
  } catch (e) {
    console.error("闸门 API 调用失败:", e.message);
    return { success: false, errMsg: "网关通信失败: " + e.message };
  }
  // ============================================================

  // 3. 如果是临时令牌，标记为已使用（一次性）
  if (tempToken && esphomeResult.success) {
    try {
      const tokenRes = await db
        .collection(COLLECTION_TEMP_TOKENS)
        .where({ token: tempToken })
        .get();
      if (tokenRes.data.length > 0) {
        await db
          .collection(COLLECTION_TEMP_TOKENS)
          .doc(tokenRes.data[0]._id)
          .update({
            data: {
              used: true,
              status: "used",
              usedTime: db.serverDate(),
            },
          });
      }
    } catch (e) {
      console.error("标记令牌已使用失败:", e);
    }
  }

  // 4. 记录到数据库
  try {
    await db.collection(COLLECTION_GATE_LOGS).add({
      data: {
        openid: operatorInfo.openid,
        nickname: operatorInfo.nickname,
        action,
        actionName: action === "open" ? "开门" : "关门",
        result: esphomeResult.success ? "success" : "fail",
        resultMsg: esphomeResult.message,
        createTime: db.serverDate(),
        operatorType: operatorInfo.type,
        tempToken: operatorInfo.token || null,
        esphomeResponse: esphomeResult,
      },
    });
  } catch (e) {
    console.error("记录日志失败:", e);
  }

  return {
    success: true,
    action,
    message: action === "open" ? "开门指令已发送" : "关门指令已发送",
  };
};

// ============================================
// 获取操作记录
// ============================================
const getGateLogs = async (event) => {
  const { limit = 20 } = event;

  const perm = await checkPermission();
  if (!perm.hasPermission) {
    return { success: false, errMsg: perm.errMsg };
  }

  try {
    const res = await db
      .collection(COLLECTION_GATE_LOGS)
      .orderBy("createTime", "desc")
      .limit(limit)
      .get();

    return {
      success: true,
      data: res.data,
    };
  } catch (e) {
    console.error("查询记录失败:", e);
    return { success: false, errMsg: "查询记录失败: " + e.message };
  }
};

// ============================================
// 获取当前用户权限信息
// ============================================
const getUserPermission = async () => {
  const wxContext = cloud.getWXContext();
  const openid = wxContext.OPENID;

  if (!openid) {
    return { hasPermission: false, errMsg: "无法获取用户身份" };
  }

  try {
    const res = await db
      .collection(COLLECTION_AUTH_USERS)
      .where({ openid })
      .get();

    return {
      hasPermission: res.data.length > 0,
      openid,
      userInfo: res.data[0] || null,
    };
  } catch (e) {
    return { hasPermission: false, errMsg: e.message };
  }
};

// ============================================
// 添加授权用户（仅管理员可用，预留）
// ============================================
const addAuthorizedUser = async (event) => {
  const { targetOpenid, nickname, role = "user" } = event;

  const perm = await checkPermission();
  if (!perm.hasPermission || perm.userInfo?.role !== "admin") {
    return { success: false, errMsg: "只有管理员可以添加用户" };
  }

  if (!targetOpenid) {
    return { success: false, errMsg: "请提供用户 openid" };
  }

  try {
    const exist = await db
      .collection(COLLECTION_AUTH_USERS)
      .where({ openid: targetOpenid })
      .get();

    if (exist.data.length > 0) {
      return { success: false, errMsg: "该用户已授权" };
    }

    await db.collection(COLLECTION_AUTH_USERS).add({
      data: {
        openid: targetOpenid,
        nickname: nickname || "未命名",
        role,
        createTime: db.serverDate(),
      },
    });

    return { success: true, message: "添加成功" };
  } catch (e) {
    return { success: false, errMsg: "添加失败: " + e.message };
  }
};

// ============================================
// 云函数入口
// ============================================
exports.main = async (event, context) => {
  switch (event.type) {
    case "checkPermission":
      return await checkPermission();
    case "checkTempToken":
      return await checkTempToken(event);
    case "createTempToken":
      return await createTempToken(event);
    case "gateControl":
      return await gateControl(event);
    case "getGateLogs":
      return await getGateLogs(event);
    case "getUserPermission":
      return await getUserPermission();
    case "addAuthorizedUser":
      return await addAuthorizedUser(event);
    default:
      return { success: false, errMsg: "未知的操作类型: " + event.type };
  }
};
