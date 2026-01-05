export interface Article {
  number: number;
  title: string;
  /** Main body clauses – preserved exactly as written, with original numbering and indentation */
  content: string;
  /** Optional précis / explanatory commentary */
  precis?: string;
}