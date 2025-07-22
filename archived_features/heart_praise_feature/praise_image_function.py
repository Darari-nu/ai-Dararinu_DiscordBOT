# 褒めメッセージ画像生成機能
# 元の場所: main.py:564-686

import os
import random
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import logging

logger = logging.getLogger(__name__)

def make_praise_image(praise_text, script_dir):
    """褒めメッセージ画像を生成する"""
    try:
        logger.info(f"画像生成開始: テキスト='{praise_text}'")
        
        # 画像のサイズを指定
        width = 1080
        height = 1520
        
        # 画像の背景色を指定
        background_color = (255, 255, 255)
        
        # 画像を生成
        image = Image.new("RGB", (width, height), background_color)
        logger.info("ベース画像作成完了")
        
        # images_homehomeフォルダの中のjpgファイル一覧を取得
        images_dir = script_dir / "images_homehome"
        logger.info(f"画像フォルダパス: {images_dir}")
        
        if images_dir.exists():
            files = [f for f in os.listdir(images_dir) if f.endswith('.jpg')]
            logger.info(f"見つかった画像ファイル数: {len(files)}")
            
            if files:
                # ランダムに1つ選ぶ
                file = random.choice(files)
                logger.info(f"選択された画像: {file}")
                
                # 画像を開く
                img_path = images_dir / file
                logger.info(f"画像パス: {img_path}")
                img = Image.open(img_path)
                
                # imageに貼り付ける
                image.paste(img, (0, 0))
                logger.info("背景画像貼り付け完了")
            else:
                logger.warning("jpg画像が見つかりませんでした")
        else:
            logger.error(f"画像フォルダが存在しません: {images_dir}")
        
        # フォントを設定（システムフォントを使用）
        try:
            # Macの場合 - より安全なフォントを使用
            font = ImageFont.truetype("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc", 30)
            logger.info("ヒラギノフォント読み込み成功")
        except Exception as e:
            logger.warning(f"ヒラギノフォント読み込み失敗: {e}")
            try:
                # Macの別のフォント
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 30)
                logger.info("Helveticaフォント読み込み成功")
            except Exception as e:
                logger.warning(f"Helveticaフォント読み込み失敗: {e}")
                try:
                    # Windowsの場合
                    font = ImageFont.truetype("C:/Windows/Fonts/msgothic.ttc", 30)
                    logger.info("MSゴシックフォント読み込み成功")
                except Exception as e:
                    logger.warning(f"MSゴシックフォント読み込み失敗: {e}")
                    # デフォルトフォント
                    font = ImageFont.load_default()
                    logger.info("デフォルトフォント使用")
        
        # テキストを処理（絵文字や特殊文字を除去）
        # 絵文字と特殊文字を除去し、ひらがな、カタカナ、漢字、英数字、基本記号のみ残す
        original_text = praise_text
        text = re.sub(r'[^\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF\u0021-\u007E]', '', praise_text)
        text = text.replace("。", "").replace("、", "").replace(" ", "").replace("ー", "┃").replace("\n", "")
        logger.info(f"テキスト処理: '{original_text}' → '{text}'")
        
        # 36文字以内に調整
        if len(text) > 36:
            text = text[:36]
            logger.info(f"36文字に短縮: '{text}'")
        
        # 9文字ずつ4行に分割
        lines = []
        for i in range(0, min(len(text), 36), 9):
            lines.append(text[i:i+9])
        
        # 4行に満たない場合は空行を追加
        while len(lines) < 4:
            lines.append("")
        
        logger.info(f"分割された行: {lines}")
        
        # 各行を縦書きに変換
        vertical_lines = []
        for line in lines:
            vertical_lines.append("\n".join(list(line)))
        
        # テキストを画像に描画
        draw = ImageDraw.Draw(image)
        
        start_x = 855
        start_y = 415
        font_size = 30
        font_offset = 4
        
        # 行数が少ない場合のオフセット調整
        start_x -= (font_size + font_offset) * (4 - len([line for line in lines if line])) // 2
        
        # 各行を縦書きで描画
        for i, vertical_line in enumerate(vertical_lines):
            x_pos = start_x - (font_size + font_offset) * i
            draw.text((x_pos, start_y), vertical_line, font=font, fill=(0, 0, 0))
            logger.info(f"行{i+1}描画完了: x={x_pos}, テキスト='{vertical_line.replace(chr(10), '')}'")
        
        # 一時ファイルとして保存
        temp_path = script_dir / "temp_praise_image.jpg"
        image.save(temp_path)
        logger.info(f"画像保存完了: {temp_path}")
        
        return str(temp_path)
        
    except Exception as e:
        logger.error(f"画像生成エラー: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None