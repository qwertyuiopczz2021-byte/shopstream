# syntax=docker/dockerfile:1
# --- build stage: Maven builds the jar inside the image, no local JDK needed ---
FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /src

# dependencies first, so they stay cached when only the sources change
COPY pom.xml .
RUN mvn -B -q dependency:go-offline

COPY src ./src
RUN mvn -B -q package -DskipTests

# --- runtime stage ---
FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /src/target/*.jar app.jar

EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
