import gymnasium as gym
from gymnasium import spaces
import numpy as np
# import gmatpy as gmat # 假設你已經裝好 GMAT API

class GmatBaseEnv(gym.Env):
    def __init__(self, config):
        super().__init__()
        self.config = config
        
        # 1. 定義動作空間 (Action Space)
        # 假設 DRL 輸出 3 個連續值，代表 X, Y, Z 方向的推力百分比 [-1.0 到 1.0]
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(3,), dtype=np.float32)

        # 2. 定義狀態空間 (Observation Space)
        # 在火箭導控或目標攔截任務中，通常包含：[X, Y, Z, Vx, Vy, Vz, 剩餘燃料]
        # 建議先將數值歸一化，但此處先以真實物理範圍為例
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(7,), dtype=np.float32)

        # 3. 啟動 GMAT 引擎並載入腳本 (虛擬碼，需依 GMAT API 實際語法調整)
        # gmat.Setup("GMAT_Bin_Path")
        # gmat.LoadScript(config.get("script_path"))
        # self.spacecraft = gmat.GetObject("Spacecraft")
        # self.propagator = gmat.GetObject("DefaultProp")

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        # 1. 將 GMAT 場景重置回初始狀態 (非常重要，否則會接續上次的軌跡)
        # 2. 重新給定太空船的初始座標、速度與燃料
        
        obs = self._get_obs()
        info = {} # 可以放入額外的除錯資訊
        return obs, info

    def step(self, action):
        # 1. 套用動作：將 RL 算出的 action 轉換並寫入 GMAT 推進器物件
        self._apply_action(action)

        # 2. 物理模擬：讓 GMAT 往前傳播一個時間步長 (例如 1 秒)
        # self.propagator.Step()

        # 3. 取得最新狀態
        obs = self._get_obs()

        # 4. 計算獎勵與判斷是否結束 (由子類別實作)
        reward = self.compute_reward(obs)
        terminated, truncated = self.check_done(obs)
        info = {}

        return obs, reward, terminated, truncated, info

    def _get_obs(self):
        """從 GMAT 讀取當前數值並打包成 numpy array"""
        # x = self.spacecraft.GetRealParameter("X")
        # vx = self.spacecraft.GetRealParameter("VX")
        # ... 依此類推
        
        # 範例防呆，實作時請替換為真實讀取邏輯
        return np.zeros(7, dtype=np.float32) 

    def _apply_action(self, action):
        """將神經網路輸出的 [-1, 1] 轉換為實際物理量並設定給 GMAT"""
        pass

    # ---------------------------------------------------------
    # 以下兩個方法強制要求繼承的子類別必須自己實作
    # ---------------------------------------------------------
    def compute_reward(self, obs):
        raise NotImplementedError

    def check_done(self, obs):
        raise NotImplementedError