/*
* Copyright 2025 Canonical Ltd.
* See LICENSE file for licensing details.
*/

package com.canonical.sampleapp.service;

import java.io.IOException;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.core.io.Resource;
import org.springframework.core.io.ResourceLoader;
import org.springframework.stereotype.Component;

import com.canonical.sampleapp.web.rest.UserController;

import software.amazon.awssdk.core.exception.SdkServiceException;
import software.amazon.awssdk.services.s3.S3Client;

@ConditionalOnProperty(name = "spring.cloud.aws.credentials.accessKey")
@Component
public class S3Service {
    private final S3Client s3Client;
    private final ResourceLoader resourceLoader;

    private final Logger log = LoggerFactory.getLogger(UserController.class);

    S3Service(S3Client s3Client, ResourceLoader resourceLoader) {
        this.s3Client = s3Client;
        this.resourceLoader = resourceLoader;
    }

    public Resource getObject(String bucketName, String key) throws IOException {
        String resourcePath = String.format("s3://%s/%s", bucketName, key);
        final Resource resource = resourceLoader.getResource(resourcePath);
        if (resource.exists()) {
            return resource;
        }
        throw new IOException(resourcePath);
    }

    public List<String> listObjectKeys(String bucketName) {
        return s3Client.listObjectsV2(builder -> builder.bucket(bucketName))
                .contents()
                .stream()
                .map(obj -> obj.key())
                .collect(Collectors.toList());
    }

    public String putObject(String bucketName, Resource resource) throws IOException {
        String key = resource.getFilename() != null ? resource.getFilename() : UUID.randomUUID().toString();
        try {
            s3Client.putObject(
                builder -> builder.bucket(bucketName).key(key),
                software.amazon.awssdk.core.sync.RequestBody.fromInputStream(resource.getInputStream(),
                    resource.contentLength()));
            return key;
        } catch (SdkServiceException e) {
            throw new IOException("Failed to upload to S3", e);
        }
    }

    public void removeObject(String bucketName, String key) throws IOException {
        try {
            s3Client.deleteObject(builder -> builder.bucket(bucketName).key(key));
        } catch (SdkServiceException e) {
            throw new IOException(String.format("Failed to delete s3://%s/%s", bucketName, key), e);
        }
    }

    public boolean checkConnection() {
        try {
            s3Client.listBuckets();
            return true;
        } catch (SdkServiceException e) {
            log.error("Failed to connect : {}", e.getMessage());
            return false;
        }
    }
}
