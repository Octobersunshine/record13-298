import io
import base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>饼图生成服务</title>
    <style>
        body {
            font-family: "Microsoft YaHei", Arial, sans-serif;
            max-width: 800px;
            margin: 40px auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .data-row {
            display: flex;
            gap: 10px;
            margin-bottom: 10px;
            align-items: center;
        }
        .data-row input {
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }
        .data-row input[type="text"] {
            flex: 1;
        }
        .data-row input[type="number"] {
            width: 120px;
        }
        .data-row button {
            background: #ff4d4f;
            color: white;
            border: none;
            padding: 8px 14px;
            border-radius: 5px;
            cursor: pointer;
        }
        .actions {
            margin-top: 20px;
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .actions button {
            padding: 10px 20px;
            font-size: 14px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }
        .btn-add {
            background: #1890ff;
            color: white;
        }
        .btn-generate {
            background: #52c41a;
            color: white;
        }
        .result {
            margin-top: 30px;
            text-align: center;
        }
        .result img {
            max-width: 100%;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .error {
            color: #ff4d4f;
            margin-top: 10px;
            padding: 10px;
            background: #fff1f0;
            border-radius: 5px;
        }
    </style>
</head>
<body>
    <h1>饼图生成服务</h1>
    <div class="container">
        <h3>输入分类和数值：</h3>
        <div id="data-rows">
            <div class="data-row">
                <input type="text" placeholder="分类名称" value="分类A">
                <input type="number" placeholder="数值" value="30" min="0">
                <button onclick="removeRow(this)">删除</button>
            </div>
            <div class="data-row">
                <input type="text" placeholder="分类名称" value="分类B">
                <input type="number" placeholder="数值" value="45" min="0">
                <button onclick="removeRow(this)">删除</button>
            </div>
            <div class="data-row">
                <input type="text" placeholder="分类名称" value="分类C">
                <input type="number" placeholder="数值" value="25" min="0">
                <button onclick="removeRow(this)">删除</button>
            </div>
        </div>
        <div class="actions">
            <button class="btn-add" onclick="addRow()">+ 添加一行</button>
            <button class="btn-generate" onclick="generatePie()">生成饼图</button>
        </div>
        <div id="error" class="error" style="display:none;"></div>
        <div id="result" class="result"></div>
    </div>

    <script>
        function addRow() {
            const container = document.getElementById('data-rows');
            const row = document.createElement('div');
            row.className = 'data-row';
            row.innerHTML = `
                <input type="text" placeholder="分类名称">
                <input type="number" placeholder="数值" min="0">
                <button onclick="removeRow(this)">删除</button>
            `;
            container.appendChild(row);
        }

        function removeRow(btn) {
            const rows = document.querySelectorAll('#data-rows .data-row');
            if (rows.length <= 1) {
                alert('至少保留一行数据');
                return;
            }
            btn.parentElement.remove();
        }

        function generatePie() {
            const rows = document.querySelectorAll('#data-rows .data-row');
            const labels = [];
            const values = [];

            for (const row of rows) {
                const inputs = row.querySelectorAll('input');
                const label = inputs[0].value.trim();
                const value = parseFloat(inputs[1].value);

                if (!label) {
                    showError('请填写所有分类名称');
                    return;
                }
                if (isNaN(value) || value < 0) {
                    showError('请填写有效的数值（大于等于0）');
                    return;
                }
                labels.push(label);
                values.push(value);
            }

            const total = values.reduce((a, b) => a + b, 0);
            if (total <= 0) {
                showError('所有数值之和必须大于0');
                return;
            }

            hideError();
            document.getElementById('result').innerHTML = '<p>正在生成...</p>';

            fetch('/api/pie', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ labels, values })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('result').innerHTML =
                        '<img src="data:image/png;base64,' + data.image + '" alt="饼图">';
                } else {
                    showError(data.error || '生成失败');
                }
            })
            .catch(err => showError('请求失败：' + err.message));
        }

        function showError(msg) {
            const el = document.getElementById('error');
            el.textContent = msg;
            el.style.display = 'block';
            document.getElementById('result').innerHTML = '';
        }

        function hideError() {
            document.getElementById('error').style.display = 'none';
        }
    </script>
</body>
</html>
"""


def merge_small_categories(labels, values, threshold=0.05):
    total = sum(values)
    if total <= 0:
        return labels, values

    merged_labels = []
    merged_values = []
    other_value = 0.0

    for label, value in zip(labels, values):
        if value / total < threshold:
            other_value += value
        else:
            merged_labels.append(label)
            merged_values.append(value)

    if other_value > 0:
        merged_labels.append('其他')
        merged_values.append(other_value)

    if len(merged_labels) < 2:
        return labels, values

    return merged_labels, merged_values


def generate_pie_chart(labels, values):
    labels, values = merge_small_categories(labels, values)

    fig, ax = plt.subplots(figsize=(8, 6))

    colors = plt.cm.Set3.colors
    if len(labels) > len(colors):
        colors = plt.cm.tab20.colors

    wedges, texts, autotexts = ax.pie(
        values,
        labels=labels,
        autopct='%1.1f%%',
        startangle=90,
        colors=colors[:len(labels)],
        pctdistance=0.85,
        textprops={'fontsize': 12}
    )

    for autotext in autotexts:
        autotext.set_color('black')
        autotext.set_fontweight('bold')

    ax.axis('equal')
    ax.set_title('数据分布饼图', fontsize=16, fontweight='bold', pad=20)

    centre_circle = plt.Circle((0, 0), 0.70, fc='white')
    fig.gca().add_artist(centre_circle)

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)

    return base64.b64encode(buf.read()).decode('utf-8')


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/pie', methods=['POST'])
def api_pie():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请提供JSON数据'}), 400

        labels = data.get('labels', [])
        values = data.get('values', [])

        if not labels or not values:
            return jsonify({'success': False, 'error': '请提供 labels 和 values 数组'}), 400

        if len(labels) != len(values):
            return jsonify({'success': False, 'error': 'labels 和 values 长度必须一致'}), 400

        if len(labels) < 2:
            return jsonify({'success': False, 'error': '至少需要2个分类'}), 400

        values = [float(v) for v in values]
        if sum(values) <= 0:
            return jsonify({'success': False, 'error': '所有数值之和必须大于0'}), 400

        image_base64 = generate_pie_chart(labels, values)
        return jsonify({'success': True, 'image': image_base64})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
