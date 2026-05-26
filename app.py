<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8" />
<title>Straw System - NVDA</title>

<style>
body{
    background:#0f1115;
    font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto;
    color:#e5e7eb;
}

.card{
    width:420px;
    padding:18px;
    border-radius:14px;
    background:#151922;
    border:1px solid #2a2f3a;
    box-shadow:0 8px 24px rgba(0,0,0,0.4);
}

.title{
    font-size:16px;
    font-weight:700;
    margin-bottom:10px;
}

.symbol{
    color:#93c5fd;
    font-weight:600;
}

.status{
    margin-top:10px;
    padding:10px;
    border-radius:10px;
    background:#1f2937;
    font-weight:600;
}

.status.warn{
    color:#fbbf24;
}

.metric{
    margin-top:10px;
    font-size:13px;
    color:#cbd5e1;
    line-height:1.6;
}

.logic{
    margin-top:12px;
    font-size:12px;
    color:#94a3b8;
    background:#0b1220;
    padding:10px;
    border-radius:10px;
}

.badge{
    display:inline-block;
    padding:2px 8px;
    border-radius:999px;
    font-size:12px;
    background:#334155;
    color:#e2e8f0;
}
</style>
</head>

<body>

<div class="card">

    <div class="title">
        Symbol：<span class="symbol">NVDA</span>
    </div>

    <div class="title">🧨 稻草一：AI资本开支循环检测</div>

    <div id="status" class="status warn">
        当前状态：🟡 过热风险
    </div>

    <div class="metric">
        核心判断：资本开支扩张速度明显高于收入增长，进入潜在泡沫扩张阶段
    </div>

    <div class="metric">
        收入增速：<span id="rev">65.47</span>% ｜ CapEx增速：<span id="capex">86.71</span>%
    </div>

    <div class="logic">
        检测逻辑：当 CapEx增速 &gt; 收入增速 × 1.2 时 → 判定为“资本过热信号”
        <br><br>
        当前计算：86.71 &gt; 65.47 × 1.2 = 78.56 → <span class="badge">触发过热</span>
    </div>

</div>

<script>
const revenue = 65.47;
const capex = 86.71;

const threshold = revenue * 1.2;
const isHot = capex > threshold;

document.getElementById("status").innerHTML =
    "当前状态：" + (isHot ? "🟡 过热风险" : "🟢 正常区间");

document.getElementById("status").className =
    "status " + (isHot ? "warn" : "");
</script>

</body>
</html>
