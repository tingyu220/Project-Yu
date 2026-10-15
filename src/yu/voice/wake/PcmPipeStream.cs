using System;
using System.IO;

// SAPI 需要可定位的 Stream；只保留最近两秒音频，禁止无限增长或磁盘落盘。
public sealed class YuPcmPipeStream : Stream
{
    private readonly Stream input;
    private readonly byte[] ring = new byte[64000];
    private long position;
    private long end;
    public YuPcmPipeStream(Stream input) { this.input = input; }
    public override bool CanRead => true;
    public override bool CanSeek => true;
    public override bool CanWrite => false;
    public override long Length => long.MaxValue;
    public override long Position { get => position; set => Seek(value, SeekOrigin.Begin); }
    public override int Read(byte[] buffer, int offset, int count)
    {
        if (position < end)
        {
            int available = (int)Math.Min(count, end - position);
            for (int i = 0; i < available; i++)
                buffer[offset + i] = ring[(position + i) % ring.Length];
            position += available;
            return available;
        }
        // 限制单次读入，保持回退缓冲边界精确。
        int wanted = Math.Min(count, ring.Length);
        int n = 0;
        // 管道的短读不代表流结束；SAPI 需要填满请求，实际 EOF 才返回短帧。
        while (n < wanted)
        {
            int read = input.Read(buffer, offset + n, wanted - n);
            if (read == 0) break;
            n += read;
        }
        for (int i = 0; i < n; i++)
            ring[(end + i) % ring.Length] = buffer[offset + i];
        end += n;
        position = end;
        return n;
    }
    public override long Seek(long offset, SeekOrigin origin)
    {
        long next = origin == SeekOrigin.Begin ? offset :
            origin == SeekOrigin.Current ? position + offset : end + offset;
        if (next < Math.Max(0, end - ring.Length) || next > end)
            throw new IOException("音频定位超过本机有界缓冲");
        return position = next;
    }
    public override void Flush() { }
    public override void SetLength(long value) { throw new NotSupportedException(); }
    public override void Write(byte[] buffer, int offset, int count) { throw new NotSupportedException(); }
}
