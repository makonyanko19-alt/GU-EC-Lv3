"use client";
import { useRef, useState } from "react";
import { yen } from "../lib/api";
import type { Method, Selection, Sku } from "../lib/types";
import { AlterationNotice } from "./Common";
export default function SelectionForm({
  sku,
  methods,
  initial,
  label = "カートに追加",
  disabled = false,
  onSubmit,
}: {
  sku: Sku;
  methods: Method[];
  initial?: Selection;
  label?: string;
  disabled?: boolean;
  onSubmit: (selection: Selection) => Promise<void>;
}) {
  const [selected, setSelected] = useState(
    initial?.alterationStatus === "SELECTED",
  );
  const [methodId, setMethodId] = useState(initial?.alterationMethodId || "");
  const [inseam, setInseam] = useState(initial?.inseamCm?.toString() || "");
  const [quantity, setQuantity] = useState(String(initial?.quantity || 1));
  const [attempted, setAttempted] = useState(false);
  const [busy, setBusy] = useState(false);
  const inFlight = useRef(false);
  const method = methods.find((m) => m.alterationMethodId === methodId);
  const n = Number(inseam),
    q = Number(quantity);
  const range = `${sku.minInseamCm}～${sku.maxInseamCm}cm`;
  let problem = "";
  if (!Number.isInteger(q) || q < 1 || q > 10)
    problem = "数量は1～10点で指定してください。";
  else if (q > sku.availableQuantity)
    problem = "在庫が不足しています。数量を減らしてください。";
  else if (selected && !sku.isAlterationAvailable)
    problem = "このサイズは裾上げ対象外です。裾上げなしを選択してください。";
  else if (selected && !method) problem = "仕上げ方法を選択してください。";
  else if (selected && !inseam.trim()) problem = "股下を入力してください。";
  else if (
    selected &&
    (!Number.isInteger(n) ||
      sku.minInseamCm === null ||
      sku.maxInseamCm === null ||
      !sku.inseamStepCm ||
      n < sku.minInseamCm ||
      n > sku.maxInseamCm ||
      (n - sku.minInseamCm) % sku.inseamStepCm !== 0)
  )
    problem = `股下は${range}、${sku.inseamStepCm}cm刻みの整数で指定してください。`;
  return (
    <form
      noValidate
      onSubmit={async (e) => {
        e.preventDefault();
        setAttempted(true);
        if (problem || inFlight.current || disabled) return;
        inFlight.current = true;
        setBusy(true);
        try {
          await onSubmit({
            quantity: q,
            alterationStatus: selected ? "SELECTED" : "NONE",
            alterationMethodId: selected ? methodId : null,
            inseamCm: selected ? n : null,
          });
        } finally {
          inFlight.current = false;
          setBusy(false);
        }
      }}
    >
      <fieldset disabled={busy || disabled}>
        <legend>数量と裾上げ</legend>
        <label>
          数量
          <input
            aria-label="数量"
            type="number"
            min="1"
            max="10"
            step="1"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
          />
        </label>
        <label>
          裾上げ
          <select
            aria-label="裾上げ"
            value={selected ? "SELECTED" : "NONE"}
            onChange={(e) => {
              const value = e.target.value === "SELECTED";
              setSelected(value);
              if (!value) {
                setMethodId("");
                setInseam("");
              }
            }}
          >
            <option value="NONE">裾上げなし</option>
            <option value="SELECTED" disabled={!sku.isAlterationAvailable}>
              裾上げあり
            </option>
          </select>
        </label>
        {!sku.isAlterationAvailable && <p>このサイズは裾上げ対象外です。</p>}
        <label>
          仕上げ方法
          <select
            aria-label="仕上げ方法"
            disabled={!selected || !sku.isAlterationAvailable}
            value={methodId}
            onChange={(e) => setMethodId(e.target.value)}
          >
            <option value="">選択してください</option>
            {methods.map((m) => (
              <option key={m.alterationMethodId} value={m.alterationMethodId}>
                {m.methodName}（{yen(m.alterationFee)} / 点）
              </option>
            ))}
          </select>
        </label>
        <label>
          股下（cm）
          <input
            aria-label="股下（cm）"
            type="number"
            step={sku.inseamStepCm || 1}
            value={inseam}
            disabled={!selected || !method || !sku.isAlterationAvailable}
            onChange={(e) => setInseam(e.target.value)}
            aria-describedby="inseam-help"
          />
        </label>
        {sku.isAlterationAvailable && (
          <p id="inseam-help" className="muted">
            {sku.sizeCode}サイズ：{range}（{sku.inseamStepCm}cm刻み）
          </p>
        )}
        {attempted && problem && (
          <p role="alert" className="field-error">
            {problem}
          </p>
        )}
        {selected && method && (
          <AlterationNotice days={method.additionalBusinessDays} />
        )}
        <p className="estimate">
          選択内容の目安{" "}
          {yen(
            (sku.sellingPrice + (selected ? method?.alterationFee || 0 : 0)) *
              (q > 0 && Number.isInteger(q) ? q : 0),
          )}
          <small>税込・送料はカートで確認</small>
        </p>
        <button disabled={!sku.isAvailable || busy || disabled} type="submit">
          {busy ? "処理中…" : label}
        </button>
      </fieldset>
    </form>
  );
}
