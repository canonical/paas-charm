/*
 * Copyright 2025 Canonical Ltd.
 * See LICENSE file for licensing details.
 */

package com.canonical.sampleapp;

import java.security.KeyManagementException;
import java.security.NoSuchAlgorithmException;
import java.security.Security;
import java.security.cert.CertificateException;
import java.security.cert.X509Certificate;

import javax.net.ssl.HostnameVerifier;
import javax.net.ssl.HttpsURLConnection;
import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLSession;
import javax.net.ssl.TrustManager;
import javax.net.ssl.X509TrustManager;

import org.bouncycastle.jce.provider.BouncyCastleProvider;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.bouncycastle.jsse.provider.BouncyCastleJsseProvider;


@SpringBootApplication
public class Application {
	
    public static void disableSslVerification() throws NoSuchAlgorithmException, KeyManagementException {
    	 TrustManager[] dummyTrustManager = new TrustManager[] { new X509TrustManager() {
    	      public java.security.cert.X509Certificate[] getAcceptedIssuers() {
    	        return null;
    	      }

			  @Override
			public void checkClientTrusted(X509Certificate[] chain, String authType) throws CertificateException {
			}

			  @Override
			public void checkServerTrusted(X509Certificate[] chain, String authType) throws CertificateException {
			}
    	    } };
    	 
    	 SSLContext sc = SSLContext.getInstance("SSL");
    	    sc.init(null, dummyTrustManager, new java.security.SecureRandom());
    	    
            HttpsURLConnection.setDefaultSSLSocketFactory(sc.getSocketFactory());
            // Create all-trusting host name verifier
            HostnameVerifier allHostsValid = new  HostnameVerifier()
            {
                @Override
                public boolean verify(String hostname, SSLSession session)
                {
                    return true;
                }
            };
            // Install the all-trusting host verifier
            HttpsURLConnection.setDefaultHostnameVerifier(allHostsValid);

    }

	

	public static void main(String[] args) throws KeyManagementException, NoSuchAlgorithmException {
		Security.addProvider(new BouncyCastleProvider());
	    Security.insertProviderAt(new BouncyCastleJsseProvider(), 2);
	    // Disabling SSL verification should not do in production code. 
	    // It is done in this example because we are using self-signed-certificates
	    // for the ingress URLs.
	    Application.disableSslVerification();


		SpringApplication.run(Application.class, args);
	}
}
