from envs.base_env import GmatBaseEnv
import os
import math
import numpy as np

class GmatPreliminaryEnv(GmatBaseEnv):
    def __init__(self, config):
        # 載入初賽專屬設定與 GMAT 腳本
        config["script_path"] = "gmat_scripts/preliminary.script"
        super().__init__(config)
        
        # 競賽官方環境常數 (根據官方公告，這裡先設假定值)
        self.T_A = config.get("T_A", 5400.0) # 假設太空船 A 軌道週期為 5400 秒
        self.k_t = config.get("k_t", 0.001)
        self.C_t = config.get("C_t", 10000.0)
        self.k_v = config.get("k_v", 0.005)
        self.C_v = config.get("C_v", 3000.0)
        
        # 追蹤競賽評分所需的變數
        self.total_delta_v = 0.0
        self.violation_count = 0
        self.previous_distance = float('inf')
        self.current_time = 0.0

    def reset(self, seed=None, options=None):
        obs, info = super().reset(seed=seed, options=options)
        
        # 回合重置時，清空追蹤變數
        self.total_delta_v = 0.0
        self.violation_count = 0
        self.current_time = 0.0
        
        # 假設 obs 的前 3 個維度是相對位置向量
        self.previous_distance = np.linalg.norm(obs[0:3])
        return obs, info

    def step(self, action):
        # 記錄這次動作消耗的 Delta V (假設 action 輸出的就是三軸速度增量 m/s)
        step_delta_v = np.linalg.norm(action)
        self.total_delta_v += step_delta_v
        
        # 檢查是否違反單次 1500 m/s 的限制 
        if step_delta_v > 1500.0:
            self.violation_count += 1
            
        obs, reward, terminated, truncated, info = super().step(action)
        
        return obs, reward, terminated, truncated, info

    def check_done(self, obs):
        """判斷任務是否結束"""
        # 解析當前狀態：假設 obs [0:3] 是太空船 A 與 B 的相對座標 (km)
        r_rel = obs[0:3]
        distance = np.linalg.norm(r_rel)
        
        # 假設從環境內部取得目前流逝時間
        self.current_time = self._get_elapsed_time() 
        
        terminated = False
        truncated = False
        
        # 成功條件：相對距離 <= 5 km 
        if distance <= 5.0:
            terminated = True
            
        # 失敗條件：超過任務時間上限 4 * T_A [cite: 23, 86]
        elif self.current_time >= 4 * self.T_A:
            truncated = True
            
        return terminated, truncated

    def compute_reward(self, obs, action, terminated, truncated):
        r_rel = obs[0:3]
        distance = np.linalg.norm(r_rel)
        
        step_reward = 0.0
        
        # ---------------------------------------------------------
        # 1. 過程中的引導性獎勵 (Dense Reward)
        # ---------------------------------------------------------
        # 鼓勵靠近：距離若比上一步縮短，給予正獎勵；若拉遠，給予負獎勵
        distance_improvement = self.previous_distance - distance
        step_reward += distance_improvement * 0.1 
        self.previous_distance = distance
        
        # 輕微的燃料懲罰，防止它亂噴推進器
        step_delta_v = np.linalg.norm(action)
        step_reward -= step_delta_v * 0.001
        
        # ---------------------------------------------------------
        # 2. 回合結束時的官方計分結算 (Terminal Reward)
        # ---------------------------------------------------------
        if terminated or truncated:
            dr_min = max(distance, 5.0)
            score_distance = 50.0 * math.exp(-(dr_min - 5.0) / 100.0)
            
            score_time = 25.0 / (1.0 + math.exp(self.k_t * (self.current_time - self.C_t)))
            
            score_fuel = 25.0 / (1.0 + math.exp(self.k_v * (self.total_delta_v - self.C_v)))
            
            penalty = self.violation_count * 10.0
            
            final_competition_score = score_distance + score_time + score_fuel - penalty
            
            final_competition_score = max(final_competition_score, 0.0)
            
            step_reward += final_competition_score * 10.0 
            
        return step_reward