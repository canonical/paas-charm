/*
* Copyright 2025 Canonical Ltd.
* See LICENSE file for licensing details.
*/

package com.canonical.sampleapp.web.rest;

import java.io.IOException;
import java.net.URI;
import java.net.URISyntaxException;
import java.util.List;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import com.canonical.sampleapp.service.S3Service;

import software.amazon.awssdk.core.exception.SdkServiceException;

@ConditionalOnProperty(name = "spring.cloud.aws.credentials.accessKey")
@RestController
@RequestMapping("/s3")
public class S3Controller {

    static final String BASE_URI = "/api/v1/buckets";

    private S3Service service;

    public S3Controller(S3Service service) {
        this.service = service;
    }

    @GetMapping("/{bucketName}/objects/{objectKey}")
    public ResponseEntity<Resource> downloadS3Object(@PathVariable String bucketName, @PathVariable String objectKey) {
        try {
            final Resource s3Object = service.getObject(bucketName, objectKey);
            return ResponseEntity.ok(s3Object);
        } catch (IOException exception) {
            return ResponseEntity.notFound().build();
        }
    }

    @GetMapping("/{bucketName}")
    public ResponseEntity<List<String>> getS3Objects(@PathVariable String bucketName) {
        try {
            List<String> keys = service.listObjectKeys(bucketName);
            return ResponseEntity.ok(keys);
        } catch (SdkServiceException exception) {
            return ResponseEntity.notFound().build();
        }
    }

    @PostMapping(path = "/{bucketName}/objects", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<Void> uploadS3Object(@PathVariable String bucketName,
            @RequestParam("file") MultipartFile file)
            throws URISyntaxException, IOException {
        if (file.isEmpty()) {
            return ResponseEntity.badRequest().build();
        }
        String objectKey = service.putObject(bucketName, file.getResource());
        URI location = new URI(String.format("/s3/%s/objects/%s", bucketName, objectKey));
        return ResponseEntity.created(location).build();
    }

    @DeleteMapping("/{bucketName}/objects/{objectKey}")
    public ResponseEntity<Void> removeObject(@PathVariable String bucketName, @PathVariable String objectKey) {
        try {
            service.removeObject(bucketName, objectKey);
            return ResponseEntity.noContent().build();
        } catch (IOException exception) {
            return ResponseEntity.notFound().build();
        }
    }

    @GetMapping("/status")
    public ResponseEntity<String> getS3Status() {
        if (service.checkConnection()) {
            return ResponseEntity.ok().body("SUCCESS");
        }
        return new ResponseEntity<>("FAILURE", HttpStatus.INTERNAL_SERVER_ERROR); // Service Unavailable
    }
}
