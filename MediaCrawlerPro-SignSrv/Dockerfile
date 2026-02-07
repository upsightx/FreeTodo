# 使用多阶段构建，从官方 Node.js 镜像获取 Node.js 和 npm
FROM node:18-slim AS nodejs

# Python 基础镜像
FROM python:3.9.19-slim

WORKDIR /app

# 从 Node.js 镜像复制 Node.js 和 npm
COPY --from=nodejs /usr/local/bin/node /usr/local/bin/
COPY --from=nodejs /usr/local/lib/node_modules /usr/local/lib/node_modules
COPY --from=nodejs /usr/local/bin/npm /usr/local/bin/
COPY --from=nodejs /usr/local/bin/npx /usr/local/bin/

# 复制 requirements.txt 并安装 Python 依赖
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 启动应用
CMD ["python", "app.py"]