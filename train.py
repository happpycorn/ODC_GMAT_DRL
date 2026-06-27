import optuna
from stable_baselines3 import PPO
from stable_baselines3.common.evaluation import evaluate_policy

from envs.preliminary_env import GmatPreliminaryEnv


def objective(trial):
    # 1. 讓 Optuna 動態決定超參數搜索範圍
    learning_rate = trial.suggest_float("learning_rate", 1e-5, 1e-3, log=True)
    gamma = trial.suggest_float("gamma", 0.9, 0.9999)
    ent_coef = trial.suggest_float("ent_coef", 1e-8, 1e-2, log=True)

    # 2. 建立環境
    # config 可以根據 trial 傳入不同的設定
    env = GmatPreliminaryEnv(config={})

    # 3. 初始化 DRL 模型
    model = PPO(
        "MlpPolicy", 
        env, 
        learning_rate=learning_rate, 
        gamma=gamma, 
        ent_coef=ent_coef,
        verbose=0 # 調參時關閉終端機輸出避免洗版
    )

    # 4. 進行短暫訓練 (例如 50,000 步)
    model.learn(total_timesteps=50000)

    # 5. 評估這組超參數的表現
    mean_reward, _ = evaluate_policy(model, env, n_eval_episodes=5)
    
    return mean_reward

if __name__ == "__main__":
    # 建立一個 Optuna Study，目標是最大化 Reward
    study = optuna.create_study(direction="maximize")
    
    # 執行 50 次超參數組合測試
    study.optimize(objective, n_trials=50)

    print("最佳超參數組合：", study.best_params)
    print("最高平均獎勵：", study.best_value)