# 使用一个轻量级的Python基础镜像
FROM registry.access.redhat.com/ubi8/python-39

# 设置工作目录
WORKDIR /app

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制Python脚本
COPY k8s_event_forwarder.py .

# 设置容器启动时要运行的命令
CMD ["python", "k8s_event_forwarder.py"]
