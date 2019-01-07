package com.litianyi.prpo;

import java.io.FileNotFoundException;
import java.io.FileReader;
import java.io.IOException;
import java.util.Enumeration;
import java.util.Map;
import java.util.Properties;
import java.util.Set;

/**
 * @Auther: ICC18e697
 * @Date: 2018/11/29 10:03
 * @Description:
 */
public class Test {
    public static void main(String[] args) throws IOException {
        Properties properties = new Properties();
        String fileName = "./a.properties";
        try (FileReader reader = new FileReader(fileName);){
            properties.load(reader);
            Set<Map.Entry<Object, Object>> entries = properties.entrySet();
            for (Map.Entry<Object, Object> entry : entries) {
                System.out.println(entry.getKey()+":"+entry.getValue());
            }
        } catch (IOException e) {
            e.printStackTrace();
        }

    }
}
