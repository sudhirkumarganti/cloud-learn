FROM maven:3.9.9-eclipse-temurin-17 AS build

WORKDIR /build
COPY pom.xml /build/pom.xml
COPY src /build/src
ENV CLOUDLEARN_CLOUDSIM_BUILD_DIR=/build/target
RUN mvn -q -Dmaven.test.skip=true -Dmaven.repo.local=/tmp/cloudlearn-m2 compile org.apache.maven.plugins:maven-jar-plugin:3.4.2:jar org.apache.maven.plugins:maven-shade-plugin:3.6.0:shade

FROM eclipse-temurin:17-jre

WORKDIR /app
COPY --from=build /build/target/cloudsim-backbone-1.0.0.jar /app/cloudsim-backbone.jar

EXPOSE 9010

ENV CLOUDLEARN_CLOUDSIM_HOST=0.0.0.0 \
    CLOUDLEARN_CLOUDSIM_PORT=9010

ENTRYPOINT ["java", "-jar", "/app/cloudsim-backbone.jar"]
