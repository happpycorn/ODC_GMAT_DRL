import optuna
import gc
from stable_baselines3 import SAC
from stable_baselines3.common.evaluation import evaluate_policy
from stable_baselines3.common.monitor import Monitor # 加入 Monitor 以獲得更好的數據追蹤

from envs.preliminary_env import GmatPreliminaryEnv

TRAINING_TIMESTEPS = 50000

def objective(trial):
    learning_rate = trial.suggest_float("learning_rate", 1e-5, 1e-3, log=True)
    gamma = trial.suggest_float("gamma", 0.9, 0.9999)
    batch_size = trial.suggest_categorical("batch_size", [64, 128, 256, 512]) # 加入 batch_size 搜索

    env = Monitor(GmatPreliminaryEnv(config={}))
    eval_env = Monitor(GmatPreliminaryEnv(config={}))

    model = SAC(
        "MlpPolicy", 
        env, 
        learning_rate=learning_rate, 
        gamma=gamma, 
        batch_size=batch_size,
        ent_coef="auto", # 使用自動熵調整機制
        verbose=0 
    )

    model.learn(total_timesteps=TRAINING_TIMESTEPS)
    mean_reward, _ = evaluate_policy(model, eval_env, n_eval_episodes=10)
    
    env.close()
    eval_env.close()
    del model
    del env
    del eval_env
    gc.collect()
    
    return mean_reward

if __name__ == "__main__":
    # n_jobs=-1 可以開啟多核心平行運算，但要注意記憶體是否足夠
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=50)

    print("最佳超參數組合：", study.best_params)
    print("最高平均獎勵：", study.best_value)