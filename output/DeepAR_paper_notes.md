# DeepAR: Probabilistic Forecasting with Autoregressive Recurrent Networks

## 📄 论文信息

| 项目 | 内容 |
|------|------|
| **标题** | DeepAR: Probabilistic Forecasting with Autoregressive Recurrent Networks |
| **作者** | David Salinas, Valentin Flunkert, Jan Gasthaus |
| **机构** | Amazon Research, Germany |
| **发表年份** | 2019 |
| **arXiv ID** | 1704.04110v3 |
| **链接** | https://arxiv.org/abs/1704.04110 |
| **代码** | https://github.com/awslabs/gluon-ts |

---

## 🎯 核心创新

### 1. 问题定义
- 需要对**大量相关时间序列**进行概率预测
- 传统方法无法有效利用跨时间序列的信息
- 间歇性需求数据（大量零值）违反传统假设（高斯误差、平稳性）

### 2. 主要贡献
1. **负二项分布似然**：专门为计数数据设计
2. **Scale handling**：处理幂律分布的尺度差异
3. **加权采样**：解决数据不平衡问题
4. **全局模型**：从所有时间序列学习共享模式

---

## 🏗️ 模型架构

### 3.1 自回归循环网络

**核心公式**：
$$h_{i,t} = h(h_{i,t-1}, z_{i,t-1}, x_{i,t}, \Theta)$$

其中：
- $h_{i,t}$：时间序列 $i$ 在时间 $t$ 的隐藏状态
- $z_{i,t-1}$：前一时刻的目标值
- $x_{i,t}$：协变量（如日期特征）
- $h$：多层LSTM网络

### 3.2 概率预测

**模型分布**：
$$Q_\Theta(z_{i,t_0:T} | z_{i,1:t_0-1}, x_{i,1:T}) = \prod_{t=t_0}^{T} \ell(z_{i,t} | \theta(h_{i,t}, \Theta))$$

### 3.3 似然函数选择

#### 高斯似然（连续数据）
$$\ell_G(z|\mu, \sigma) = (2\pi\sigma^2)^{-1/2} \exp(-(z-\mu)^2/(2\sigma^2))$$

$$\mu(h_{i,t}) = w_\mu^T h_{i,t} + b_\mu$$
$$\sigma(h_{i,t}) = \log(1 + \exp(w_\sigma^T h_{i,t} + b_\sigma))$$

#### ⭐ 负二项分布似然（计数数据/间歇性需求）
$$\ell_{NB}(z|\mu, \alpha) = \frac{\Gamma(z + 1/\alpha)}{\Gamma(z+1)\Gamma(1/\alpha)} \left(\frac{1}{1+\alpha\mu}\right)^{1/\alpha} \left(\frac{\alpha\mu}{1+\alpha\mu}\right)^z$$

其中：
- $\mu$：均值参数
- $\alpha$：形状参数，控制方差相对于均值的比例
- $\text{Var}[z] = \mu + \mu^2 \alpha$

**关键点**：负二项分布特别适合**稀疏、过度离散**的计数数据！

---

## 🔧 关键技术

### 4.1 Scale Handling（尺度处理）

**问题**：不同时间序列的量级差异巨大（幂律分布）

**解决方案**：
1. **输入缩放**：将自回归输入除以尺度因子 $\nu_i$
2. **输出反缩放**：将似然参数乘以 $\nu_i$

$$\nu_i = 1 + \frac{1}{t_0} \sum_{t=1}^{t_0} z_{i,t}$$

对于负二项分布：
$$\mu = \nu_i \log(1 + \exp(o_\mu))$$
$$\alpha = \log(1 + \exp(o_\alpha)) / \sqrt{\nu_i}$$

### 4.2 加权采样（Weighted Sampling）

**问题**：幂律分布导致高频时间序列被欠采样

**解决方案**：采样概率与尺度因子 $\nu_i$ 成正比

$$P(\text{选择时间序列} i) \propto \nu_i$$

### 4.3 协变量特征

| 特征类型 | 示例 |
|----------|------|
| 时间相关 | 星期几、小时、月份、年份 |
| 项目相关 | 产品类别、商店位置 |
| 外部因素 | 价格、促销状态 |

---

## 📊 实验结果

### 5.1 数据集

| 数据集 | 时间序列数 | 时间粒度 | 领域 |
|--------|------------|----------|------|
| parts | 1,046 | 月 | 汽车零件销售 |
| electricity | 370 | 小时 | 电力消耗 |
| traffic | 963 | 小时 | 交通占用率 |
| ec-sub | 39,700 | 周 | Amazon零售 |
| ec | 534,884 | 周 | Amazon零售 |

### 5.2 主要结果

**与传统方法对比**（相对于基线的归一化指标，越低越好）：

| 方法 | parts (0.5-risk) | ec-sub (0.5-risk) | ec (0.5-risk) |
|------|------------------|-------------------|---------------|
| Croston | 1.47 | 1.29 | 1.30 |
| ETS | 1.28 | 0.83 | 0.77 |
| ISSM | 1.04 | 1.00 | 1.00 |
| **DeepAR** | **0.98** | **0.64** | **0.59** |

**关键发现**：
1. DeepAR在所有数据集上显著优于传统方法
2. 负二项分布比高斯分布更适合计数数据
3. Scale handling和加权采样对幂律分布数据至关重要

### 5.3 与矩阵分解对比

| 数据集 | 方法 | ND | RMSE |
|--------|------|-----|------|
| electricity | MatFact | 0.16 | 1.15 |
| electricity | **DeepAR** | **0.07** | **1.00** |
| traffic | MatFact | 0.20 | 0.43 |
| traffic | **DeepAR** | **0.17** | **0.42** |

---

## 🔑 关键洞察

### 6.1 与间歇性需求的关联

1. **负二项分布**：
   - 自然处理大量零值
   - 建模过度离散数据
   - 参数化便于网络输出

2. **Scale handling**：
   - 处理不同产品销量的巨大差异
   - 避免高频产品主导训练

3. **加权采样**：
   - 确保低频（间歇性）产品也被充分学习

### 6.2 概率预测的优势

1. **不确定性量化**：提供置信区间
2. **决策优化**：支持风险最小化决策
3. **校准性好**：预测分布与实际观测匹配

---

## 💻 实现细节

### 7.1 超参数

| 参数 | parts | electricity | traffic | ec-sub | ec |
|------|-------|-------------|---------|--------|-----|
| 编码器长度 | 8 | 168 | 168 | 52 | 52 |
| 解码器长度 | 8 | 24 | 24 | 52 | 52 |
| LSTM层数 | 3 | 3 | 3 | 3 | 3 |
| LSTM节点数 | 40 | 40 | 40 | 120 | 120 |
| 批量大小 | 64 | 64 | 64 | 512 | 512 |
| 学习率 | 1e-3 | 1e-3 | 1e-3 | 5e-3 | 5e-3 |

### 7.2 训练细节

- **优化器**：Adam
- **早停**：使用验证集
- **预测采样**：200个样本
- **框架**：MXNet

### 7.3 代码仓库

```
https://github.com/awslabs/gluon-ts
```

GluonTS是Amazon开源的时间序列概率预测工具包，包含DeepAR的完整实现。

---

## 📚 相关论文引用

1. **Croston方法**（1972）：间歇性需求预测的经典方法
2. **Snyder等**（2012）：负二项自回归方法
3. **Seeger等**（2016）：贝叶斯间歇性需求预测（ISSM）
4. **Hyndman等**（2008）：指数平滑状态空间模型

---

## 🎓 总结

### DeepAR的核心优势

1. ✅ **全局学习**：从数百万时间序列学习共享模式
2. ✅ **灵活似然**：支持高斯、负二项等多种分布
3. ✅ **尺度处理**：自动适应不同量级的数据
4. ✅ **概率输出**：提供完整的预测分布
5. ✅ **冷启动**：能预测新产品/新时间序列

### 适用场景

- ✅ 大规模零售需求预测
- ✅ 间歇性需求预测（备件、奢侈品）
- ✅ 能源消耗预测
- ✅ 任何需要概率预测的场景

### 局限性

- ❌ 自回归误差累积
- ❌ 需要大量相关时间序列
- ❌ 对长期依赖建模有限

---

## 📖 引用格式

```bibtex
@article{salinas2019deepar,
  title={DeepAR: Probabilistic forecasting with autoregressive recurrent networks},
  author={Salinas, David and Flunkert, Valentin and Gasthaus, Jan},
  journal={International Journal of Forecasting},
  volume={36},
  number={3},
  pages={1181--1191},
  year={2020},
  publisher={Elsevier}
}
```
