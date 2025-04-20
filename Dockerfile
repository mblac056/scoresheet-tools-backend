FROM public.ecr.aws/lambda/python:3.11

# Install Java 11 for tabula-py
RUN yum update -y && \
    yum install -y java-11-amazon-corretto && \
    yum clean all

ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk
ENV PATH="${JAVA_HOME}/bin:${PATH}"

# Copy source files
COPY parser.py app.py lambda_handler.py requirements.txt ./

# Install Python dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Set the Lambda handler
CMD ["lambda_handler.handler"]
