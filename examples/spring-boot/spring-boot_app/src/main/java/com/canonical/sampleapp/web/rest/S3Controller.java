package com.canonical.sampleapp.web.rest;

import java.io.File;
import java.io.IOException;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import com.canonical.sampleapp.service.S3Service;

@RestController
@RequestMapping("/s3")
public class S3Controller {

    @Autowired
    private S3Service s3Service;

    // Upload a file to S3
    @PostMapping("/upload")
    public String uploadFile(@RequestParam("file") MultipartFile file) throws IOException {
        File convFile = new File(file.getOriginalFilename());
        file.transferTo(convFile); // Convert MultipartFile to File
        return s3Service.uploadFile(convFile);
    }

    // Download a file from S3
    @GetMapping("/download/{fileName}")
    public String downloadFile(@PathVariable String fileName) {
        return s3Service.downloadFile(fileName).getKey();
    }
}