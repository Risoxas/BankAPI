FROM python:3
WORKDIR /user/src/app
COPY requirements.txt ./
RUN pip install --no-cache -r requirements.txt
COPY . .
ENV PYTHONUNBUFFERED=1
RUN echo "source activate my_env" > ~/.bashrc
ENV PATH /opt/conda/envs/my_env/bin:$PATH
CMD ["python","app.py"]