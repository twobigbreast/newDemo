package com.litianyi.inters;

import java.text.SimpleDateFormat;
import java.time.format.DateTimeFormatter;
import java.util.Date;

/**
 * @Auther: ICC18e697
 * @Date: 2018/11/26 15:30
 * @Description:
 */
public class FileTest {
    public static void main(String[] args) {
        String s="001020-LSJ_LN_087-20181023013610625.ifsi";
        String[] split = s.split("-");
        int i = split.length - 1;
        String s1 = split[i];
        String substring = s1.substring(0,8);
        int i1 = Integer.parseInt(substring);
        String yyyyMMdd = formatToString(new Date(), "yyyyMMdd");
        int i2 = Integer.parseInt(yyyyMMdd);



    }


    //将date转化为string
    public static String formatToString(Date date, String pattern) {
        final SimpleDateFormat format = new SimpleDateFormat(pattern);
        String format1 = format.format(date);
        return format1;
    }
}
